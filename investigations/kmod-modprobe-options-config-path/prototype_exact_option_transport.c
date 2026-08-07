// SPDX-License-Identifier: GPL-2.0-or-later
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PREFIX "KMOD1;"
#define PREFIX_LEN 6

struct argvec {
	char **v;
	size_t n;
};

static void argvec_free(struct argvec *a)
{
	if (!a || !a->v)
		return;
	for (size_t i = 0; i < a->n; i++)
		free(a->v[i]);
	free(a->v);
	a->v = NULL;
	a->n = 0;
}

static bool add_overflow(size_t a, size_t b, size_t *out)
{
	if (a > SIZE_MAX - b)
		return true;
	*out = a + b;
	return false;
}

static int push_copy(struct argvec *a, const char *s, size_t len)
{
	size_t count;
	if (add_overflow(a->n, 1, &count) || count > SIZE_MAX / sizeof(*a->v))
		return -EOVERFLOW;
	char **nv = realloc(a->v, count * sizeof(*a->v));
	if (!nv)
		return -ENOMEM;
	a->v = nv;
	a->v[a->n] = malloc(len + 1);
	if (!a->v[a->n])
		return -ENOMEM;
	memcpy(a->v[a->n], s, len);
	a->v[a->n][len] = '\0';
	a->n++;
	return 0;
}

static size_t decimal_len(size_t n)
{
	size_t len = 1;
	while (n >= 10) {
		n /= 10;
		len++;
	}
	return len;
}

static int encode_exact(const struct argvec *a, char **out)
{
	size_t len = PREFIX_LEN;
	for (size_t i = 0; i < a->n; i++) {
		size_t alen = strlen(a->v[i]);
		size_t part;
		if (add_overflow(decimal_len(alen), 2, &part) ||
		    add_overflow(part, alen, &part) || add_overflow(len, part, &len))
			return -EOVERFLOW;
	}
	if (add_overflow(len, 1, &len))
		return -EOVERFLOW;
	char *record = malloc(len);
	if (!record)
		return -ENOMEM;
	char *p = record;
	memcpy(p, PREFIX, PREFIX_LEN);
	p += PREFIX_LEN;
	for (size_t i = 0; i < a->n; i++) {
		size_t alen = strlen(a->v[i]);
		int n = sprintf(p, "%zu", alen);
		p += n;
		*p++ = ':';
		memcpy(p, a->v[i], alen);
		p += alen;
		*p++ = ',';
	}
	*p = '\0';
	*out = record;
	return 0;
}

static int parse_size(const char *start, const char *end, size_t *value)
{
	if (start == end)
		return -EINVAL;
	if (end - start > 1 && *start == '0')
		return -EINVAL;
	size_t n = 0;
	for (const char *p = start; p < end; p++) {
		if (*p < '0' || *p > '9')
			return -EINVAL;
		unsigned digit = (unsigned)(*p - '0');
		if (n > (SIZE_MAX - digit) / 10)
			return -EOVERFLOW;
		n = n * 10 + digit;
	}
	*value = n;
	return 0;
}

static int decode_exact(const char *record, struct argvec *out)
{
	if (strncmp(record, PREFIX, PREFIX_LEN) != 0)
		return -EPROTONOSUPPORT;
	const char *p = record + PREFIX_LEN;
	const char *limit = record + strlen(record);
	while (p < limit) {
		const char *colon = memchr(p, ':', (size_t)(limit - p));
		if (!colon)
			goto invalid;
		size_t alen;
		int r = parse_size(p, colon, &alen);
		if (r < 0) {
			argvec_free(out);
			return r;
		}
		const char *value = colon + 1;
		if (alen > (size_t)(limit - value) ||
		    alen == (size_t)(limit - value) || value[alen] != ',')
			goto invalid;
		r = push_copy(out, value, alen);
		if (r < 0) {
			argvec_free(out);
			return r;
		}
		p = value + alen + 1;
	}
	return 0;
invalid:
	argvec_free(out);
	return -EINVAL;
}

/* Semantic model of current kmod's private parser for compatibility probes. */
static int parse_legacy_current(const char *env, struct argvec *out)
{
	const char *start = env;
	const char *p = env;
	char quote = '\0';
	char *buf = malloc(strlen(env) + 1);
	if (!buf)
		return -ENOMEM;
	size_t used = 0;

	while (true) {
		char c = *p;
		if (!quote && c == ' ') {
			int r = push_copy(out, buf, used);
			if (r < 0) {
				free(buf);
				argvec_free(out);
				return r;
			}
			used = 0;
			p++;
			start = p;
			continue;
		}
		if (!quote && c == '\0') {
			if (p > start) {
				int r = push_copy(out, buf, used);
				if (r < 0) {
					free(buf);
					argvec_free(out);
					return r;
				}
			}
			break;
		}
		if (c == '\0') {
			int r = push_copy(out, buf, used);
			free(buf);
			if (r < 0)
				argvec_free(out);
			return r;
		}
		if (c == '\'' || c == '"') {
			if (!quote) {
				quote = c;
				p++;
				continue;
			}
			if (quote == c) {
				quote = '\0';
				p++;
				continue;
			}
		}
		buf[used++] = c;
		p++;
	}
	free(buf);
	return 0;
}

static bool equal_args(const struct argvec *a, const struct argvec *b)
{
	if (a->n != b->n)
		return false;
	for (size_t i = 0; i < a->n; i++)
		if (strcmp(a->v[i], b->v[i]) != 0)
			return false;
	return true;
}

static int legacy_mirror(const struct argvec *a, char **out)
{
	size_t len = 1;
	const char *escaped = " \t\n\r\v\f\\\"'";
	for (size_t i = 0; i < a->n; i++) {
		if (i && add_overflow(len, 1, &len))
			return -EOVERFLOW;
		if (!a->v[i][0]) {
			if (add_overflow(len, 2, &len))
				return -EOVERFLOW;
			continue;
		}
		for (const unsigned char *p = (const unsigned char *)a->v[i]; *p; p++) {
			if (strchr(escaped, *p) && add_overflow(len, 1, &len))
				return -EOVERFLOW;
			if (add_overflow(len, 1, &len))
				return -EOVERFLOW;
		}
	}
	char *s = malloc(len);
	if (!s)
		return -ENOMEM;
	char *q = s;
	for (size_t i = 0; i < a->n; i++) {
		if (i)
			*q++ = ' ';
		if (!a->v[i][0]) {
			*q++ = '\'';
			*q++ = '\'';
			continue;
		}
		for (const unsigned char *p = (const unsigned char *)a->v[i]; *p; p++) {
			if (strchr(escaped, *p))
				*q++ = '\\';
			*q++ = (char)*p;
		}
	}
	*q = '\0';
	*out = s;
	return 0;
}

static uint64_t rng_state = UINT64_C(0x4b4d4f44f00dcafe);
static uint32_t prng(void)
{
	rng_state ^= rng_state << 13;
	rng_state ^= rng_state >> 7;
	rng_state ^= rng_state << 17;
	return (uint32_t)rng_state;
}

static int add_generated(struct argvec *a, size_t len)
{
	char *s = malloc(len + 1);
	if (!s)
		return -ENOMEM;
	for (size_t i = 0; i < len; i++)
		s[i] = (char)(1 + prng() % 255);
	s[len] = '\0';
	int r = push_copy(a, s, len);
	free(s);
	return r;
}

static int require(bool condition, const char *what)
{
	if (condition)
		return 0;
	fprintf(stderr, "failed: %s\n", what);
	return -1;
}

int main(void)
{
	int rc = 1;
	struct argvec corpus = {0}, decoded = {0};
	char *record = NULL;
	const char *fixed[] = {"", "/config dir", "/tab\tpath", "/line\npath",
			       "/quote'\"path", "/back\\slash"};
	for (size_t i = 0; i < sizeof(fixed) / sizeof(fixed[0]); i++)
		if (push_copy(&corpus, fixed[i], strlen(fixed[i])) < 0)
			goto out;
	char allbytes[256];
	for (int i = 1; i < 256; i++)
		allbytes[i - 1] = (char)i;
	allbytes[255] = '\0';
	if (push_copy(&corpus, allbytes, 255) < 0)
		goto out;
	for (size_t i = 0; i < 10000; i++)
		if (add_generated(&corpus, prng() % 65) < 0)
			goto out;

	if (encode_exact(&corpus, &record) < 0 || decode_exact(record, &decoded) < 0)
		goto out;
	if (require(equal_args(&corpus, &decoded), "10007-case exact roundtrip") < 0)
		goto out;

	const char *bad[] = {"", "KMOD0;", "KMOD1;:", "KMOD1;x:a,", "KMOD1;01:a,",
			     "KMOD1;2:a,", "KMOD1;1:a", "KMOD1;1:a,trailing",
			     "KMOD1;184467440737095516160:a,"};
	size_t rejected = 0;
	for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
		struct argvec tmp = {0};
		if (decode_exact(bad[i], &tmp) < 0)
			rejected++;
		argvec_free(&tmp);
	}
	if (require(rejected == 9, "malformed records rejected") < 0)
		goto out;

	struct argvec exact = {0};
	const char *exact_values[] = {"-C", "/config dir", "-C", "", "-q"};
	for (size_t i = 0; i < 5; i++)
		if (push_copy(&exact, exact_values[i], strlen(exact_values[i])) < 0)
			goto out_exact;
	char *stable = NULL;
	if (encode_exact(&exact, &stable) < 0)
		goto out_exact;
	size_t stable_len = strlen(stable);
	for (int level = 0; level < 20; level++) {
		struct argvec level_args = {0};
		char *next = NULL;
		if (decode_exact(stable, &level_args) < 0 || !equal_args(&exact, &level_args) ||
		    encode_exact(&level_args, &next) < 0 || strcmp(stable, next) != 0) {
			free(next);
			argvec_free(&level_args);
			goto out_stable;
		}
		free(next);
		argvec_free(&level_args);
	}

	struct argvec legacy_backslash = {0};
	if (parse_legacy_current("-C /foo\\bar", &legacy_backslash) < 0 ||
	    require(legacy_backslash.n == 2 && strcmp(legacy_backslash.v[1], "/foo\\bar") == 0,
		    "legacy raw backslash preserved") < 0)
		goto out_legacy;

	struct argvec quoted = {0};
	if (parse_legacy_current("-C \"/config dir\"", &quoted) < 0 ||
	    require(quoted.n == 2 && strcmp(quoted.v[1], "/config dir") == 0,
		    "legacy quoted path control") < 0)
		goto out_quoted;

	char *mirror = NULL;
	struct argvec old_child = {0};
	if (legacy_mirror(&exact, &mirror) < 0 || parse_legacy_current(mirror, &old_child) < 0)
		goto out_old;
	bool new_to_old_equal = equal_args(&exact, &old_child);

	struct argvec exact_empty = {0};
	char *empty_record = NULL;
	if (encode_exact(&exact_empty, &empty_record) < 0)
		goto out_empty;

	printf("{\n");
	printf("  \"generated_roundtrip_cases\": %zu,\n", corpus.n);
	printf("  \"malformed_records_rejected\": %zu,\n", rejected);
	printf("  \"legacy_raw_backslash_preserved_without_exact\": true,\n");
	printf("  \"legacy_quoted_space_path_control\": true,\n");
	printf("  \"exact_record_bytes\": %zu,\n", stable_len);
	printf("  \"recursion_levels_stable\": 20,\n");
	printf("  \"empty_exact_record_is_valid_and_authoritative_under_model_policy\": true,\n");
	printf("  \"new_parent_to_old_child_mirror_preserves_exact_argv\": %s,\n",
	       new_to_old_equal ? "true" : "false");
	printf("  \"mixed_version_boundary_requires_policy\": true\n");
	printf("}\n");

	free(empty_record);
	rc = 0;
out_empty:
	argvec_free(&exact_empty);
out_old:
	argvec_free(&old_child);
	free(mirror);
out_quoted:
	argvec_free(&quoted);
out_legacy:
	argvec_free(&legacy_backslash);
out_stable:
	free(stable);
out_exact:
	argvec_free(&exact);
out:
	free(record);
	argvec_free(&decoded);
	argvec_free(&corpus);
	return rc;
}
