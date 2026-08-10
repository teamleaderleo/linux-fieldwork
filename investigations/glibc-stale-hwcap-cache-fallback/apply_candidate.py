#!/usr/bin/env python3
"""Apply the current internal glibc stale-cache candidate prototype.

The transformation is intentionally exact-source-bound.  It refuses if any
reviewed source block has changed instead of fuzzily applying across revisions.
"""

from __future__ import annotations

import pathlib
import sys


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one source block, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} GLIBC_SOURCE_ROOT")
    root = pathlib.Path(sys.argv[1]).resolve()

    ldsodefs = root / "sysdeps/generic/ldsodefs.h"
    dl_cache = root / "elf/dl-cache.c"
    dl_load = root / "elf/dl-load.c"
    test = root / "elf/tst-glibc-hwcaps-prepend-cache.c"

    replace_once(
        ldsodefs,
        """/* Look up NAME in ld.so.cache and return the file name stored there,\n   or null if none is found.  Caller must free returned string.  */\nextern char *_dl_load_cache_lookup (const char *name) attribute_hidden;\n""",
        """/* Look up NAME in ld.so.cache and return the file name stored there,\n   or null if none is found.  Caller must free returned string.  */\nextern char *_dl_load_cache_lookup (const char *name) attribute_hidden;\n\n/* Return all cache candidates for NAME in loader preference order.  The\n   returned vector and each non-null string are separately allocated.  The\n   caller owns them.  Cache data is copied before any allocation which may\n   recursively re-enter the loader.  */\nextern char **_dl_load_cache_lookup_candidates (const char *name)\n  attribute_hidden;\n""",
    )

    helper_anchor = "\nint\n_dl_cache_libcmp (const char *p1, const char *p2)\n"
    helper = r'''

struct cache_candidate_copy
{
  size_t offset;
  size_t length;
  uint32_t priority;
  uint32_t order;
  bool ordinary;
};

/* Find the complete comparator-equivalent cache-name group for NAME.  */
static bool
cache_name_range (const char *string_table, uint32_t string_table_size,
                  const struct file_entry *libs, uint32_t nlibs,
                  uint32_t entry_size, const char *name,
                  uint32_t *first, uint32_t *last)
{
  int left = 0;
  int right = nlibs - 1;

  while (left <= right)
    {
      int middle = (left + right) / 2;
      uint32_t key = _dl_cache_file_entry (libs, entry_size, middle)->key;
      if (!_dl_cache_verify_ptr (key, string_table_size))
        return false;

      int cmpres = _dl_cache_libcmp (name, string_table + key);
      if (cmpres == 0)
        {
          int begin = middle;
          int end = middle;
          while (begin > 0)
            {
              key = _dl_cache_file_entry (libs, entry_size, begin - 1)->key;
              if (!_dl_cache_verify_ptr (key, string_table_size)
                  || _dl_cache_libcmp (name, string_table + key) != 0)
                break;
              --begin;
            }
          while (end + 1 < nlibs)
            {
              key = _dl_cache_file_entry (libs, entry_size, end + 1)->key;
              if (!_dl_cache_verify_ptr (key, string_table_size)
                  || _dl_cache_libcmp (name, string_table + key) != 0)
                break;
              ++end;
            }
          *first = begin;
          *last = end;
          return true;
        }

      if (cmpres < 0)
        left = middle + 1;
      else
        right = middle - 1;
    }

  return false;
}

/* Classify one cache entry which is already known to be in NAME's group.  */
static bool
cache_candidate_info (const char *string_table, uint32_t string_table_size,
                      const struct file_entry *libs, uint32_t entry_size,
                      uint32_t index, const char **path, bool *named_hwcap,
                      uint32_t *priority)
{
  const struct file_entry *lib
    = _dl_cache_file_entry (libs, entry_size, index);
  if (!_dl_cache_check_flags (lib->flags)
      || !_dl_cache_verify_ptr (lib->value, string_table_size))
    return false;

  bool named = false;
  uint32_t candidate_priority = 0;
  if (entry_size >= sizeof (struct file_entry_new))
    {
      const struct file_entry_new *libnew = (const void *) lib;
#ifdef SHARED
      named = dl_cache_hwcap_extension (libnew);
      if (named)
        {
          if (!dl_cache_hwcap_isa_level_compatible (libnew))
            return false;
          candidate_priority = glibc_hwcaps_priority (libnew->hwcap);
          if (candidate_priority == 0)
            return false;
        }
#endif
      if (!named && libnew->hwcap != 0)
        return false;
    }

  *path = string_table + lib->value;
  *named_hwcap = named;
  *priority = candidate_priority;
  return true;
}

static bool
cache_candidate_before (const struct cache_candidate_copy *left,
                        const struct cache_candidate_copy *right)
{
  if (left->ordinary != right->ordinary)
    return !left->ordinary;
  if (!left->ordinary && left->priority != right->priority)
    return left->priority < right->priority;
  return left->order < right->order;
}

/* Copy all useful cache alternatives for NAME before returning to dl-load.
   Named HWCAP entries are ordered by runtime priority.  Equal-priority entries
   retain cache order.  The ordinary fallback is the same entry current cache
   lookup would choose if no named HWCAP entry were available.  */
static char **
search_cache_candidates (const char *string_table, uint32_t string_table_size,
                         const struct file_entry *libs, uint32_t nlibs,
                         uint32_t entry_size, const char *name)
{
  uint32_t first;
  uint32_t last;
  if (!cache_name_range (string_table, string_table_size, libs, nlibs,
                         entry_size, name, &first, &last))
    return NULL;

  size_t named_count = 0;
  size_t string_bytes = 0;
  uint32_t baseline_index = UINT32_MAX;

  for (uint32_t index = first; index <= last; ++index)
    {
      const char *path;
      bool named;
      uint32_t priority;
      if (!cache_candidate_info (string_table, string_table_size, libs,
                                 entry_size, index, &path, &named, &priority))
        continue;

      if (named)
        {
          ++named_count;
          string_bytes += strlen (path) + 1;
        }
      else
        {
          baseline_index = index;
          const struct file_entry *lib
            = _dl_cache_file_entry (libs, entry_size, index);
          if (lib->flags == _DL_CACHE_DEFAULT_ID)
            break;
        }
    }

  size_t count = named_count;
  if (baseline_index != UINT32_MAX)
    {
      const char *path;
      bool named;
      uint32_t priority;
      if (cache_candidate_info (string_table, string_table_size, libs,
                                entry_size, baseline_index, &path, &named,
                                &priority))
        {
          ++count;
          string_bytes += strlen (path) + 1;
        }
    }

  if (count == 0)
    return NULL;

  size_t record_bytes = count * sizeof (struct cache_candidate_copy);
  struct dl_scratch_buffer scratch = dl_scratch_buffer_init ();
  dl_scratch_buffer_allocate (&scratch, record_bytes + string_bytes,
                              DL_SCRATCH_NO_MALLOC);
  struct cache_candidate_copy *records = scratch.data;
  char *cursor = (char *) scratch.data + record_bytes;
  size_t written = 0;

  for (uint32_t index = first; index <= last; ++index)
    {
      const char *path;
      bool named;
      uint32_t priority;
      if (!cache_candidate_info (string_table, string_table_size, libs,
                                 entry_size, index, &path, &named, &priority)
          || !named)
        continue;

      size_t length = strlen (path) + 1;
      records[written] = (struct cache_candidate_copy)
        {
          .offset = cursor - (char *) scratch.data,
          .length = length,
          .priority = priority,
          .order = index,
          .ordinary = false,
        };
      memcpy (cursor, path, length);
      cursor += length;
      ++written;
    }

  if (baseline_index != UINT32_MAX)
    {
      const char *path;
      bool named;
      uint32_t priority;
      if (cache_candidate_info (string_table, string_table_size, libs,
                                entry_size, baseline_index, &path, &named,
                                &priority))
        {
          size_t length = strlen (path) + 1;
          records[written] = (struct cache_candidate_copy)
            {
              .offset = cursor - (char *) scratch.data,
              .length = length,
              .priority = 0,
              .order = baseline_index,
              .ordinary = true,
            };
          memcpy (cursor, path, length);
          cursor += length;
          ++written;
        }
    }

  assert (written == count);
  for (size_t index = 1; index < count; ++index)
    {
      struct cache_candidate_copy candidate = records[index];
      size_t position = index;
      while (position > 0
             && cache_candidate_before (&candidate, &records[position - 1]))
        {
          records[position] = records[position - 1];
          --position;
        }
      records[position] = candidate;
    }

  char **result = malloc ((count + 1) * sizeof (*result));
  if (result == NULL)
    {
      dl_scratch_buffer_free (&scratch);
      return NULL;
    }

  for (size_t index = 0; index < count; ++index)
    {
      result[index] = __strdup ((char *) scratch.data + records[index].offset);
      if (result[index] == NULL)
        {
          while (index > 0)
            free (result[--index]);
          free (result);
          dl_scratch_buffer_free (&scratch);
          return NULL;
        }
    }
  result[count] = NULL;
  dl_scratch_buffer_free (&scratch);
  return result;
}

char **
_dl_load_cache_lookup_candidates (const char *name)
{
  if (__glibc_unlikely (GLRO(dl_debug_mask) & DL_DEBUG_LIBS))
    _dl_debug_printf (" search cache=%s\n", LD_SO_CACHE);

  if (_dl_check_ldsocache_needs_loading ())
    _dl_maybe_load_ldsocache ();
  if (cache == NULL)
    return NULL;

  if (cache_new != NULL)
    {
      const char *string_table = (const char *) cache_new;
      return search_cache_candidates (string_table, cachesize,
                                      &cache_new->libs[0].entry,
                                      cache_new->nlibs,
                                      sizeof (cache_new->libs[0]), name);
    }

  const char *string_table = (const char *) &cache->libs[cache->nlibs];
  uint32_t string_table_size
    = (const char *) cache + cachesize - string_table;
  return search_cache_candidates (string_table, string_table_size,
                                  &cache->libs[0], cache->nlibs,
                                  sizeof (cache->libs[0]), name);
}
'''
    replace_once(dl_cache, helper_anchor, helper + helper_anchor)

    old_cache_block = r'''#ifdef USE_LDCONFIG
      if (fd == -1
	  && (__glibc_likely ((mode & __RTLD_SECURE) == 0)
	      || ! __libc_enable_secure)
	  && __glibc_likely (GLRO(dl_inhibit_cache) == 0))
	{
	  /* Check the list of libraries in the file /etc/ld.so.cache,
	     for compatibility with Linux's ldconfig program.  */
	  char *cached = _dl_load_cache_lookup (name);

	  if (cached != NULL)
	    {
	      // XXX Correct to unconditionally default to namespace 0?
	      l = (loader
		   ?: GL(dl_ns)[LM_ID_BASE]._ns_loaded
# ifdef SHARED
		   ?: &_dl_rtld_map
# endif
		  );

	      /* If the loader has the DF_1_NODEFLIB flag set we must not
		 use a cache entry from any of these directories.  */
	      if (__glibc_unlikely (l->l_flags_1 & DF_1_NODEFLIB))
		{
		  const char *dirp = system_dirs;
		  unsigned int cnt = 0;

		  do
		    {
		      if (memcmp (cached, dirp, system_dirs_len[cnt]) == 0)
			{
			  /* The prefix matches.  Don't use the entry.  */
			  free (cached);
			  cached = NULL;
			  break;
			}

		      dirp += system_dirs_len[cnt] + 1;
		      ++cnt;
		    }
		  while (cnt < nsystem_dirs_len);
		}

	      if (cached != NULL)
		{
		  fd = open_verify (cached, -1,
				    &fb, loader ?: GL(dl_ns)[nsid]._ns_loaded,
				    LA_SER_CONFIG, mode, &found_other_class,
				    false);
		  if (__glibc_likely (fd != -1))
		    realname = cached;
		  else
		    free (cached);
		}
	    }
	}
#endif
'''
    new_cache_block = r'''#ifdef USE_LDCONFIG
      if (fd == -1
	  && (__glibc_likely ((mode & __RTLD_SECURE) == 0)
	      || ! __libc_enable_secure)
	  && __glibc_likely (GLRO(dl_inhibit_cache) == 0))
	{
	  /* Check all compatible alternatives recorded in /etc/ld.so.cache
	     before leaving cache semantics for the ordinary default path.  */
	  char **cached = _dl_load_cache_lookup_candidates (name);

	  if (cached != NULL)
	    {
	      // XXX Correct to unconditionally default to namespace 0?
	      l = (loader
		   ?: GL(dl_ns)[LM_ID_BASE]._ns_loaded
# ifdef SHARED
		   ?: &_dl_rtld_map
# endif
		  );

	      for (size_t index = 0; cached[index] != NULL; ++index)
		{
		  bool use_candidate = true;

		  /* If the loader has the DF_1_NODEFLIB flag set, skip cache
		     entries from default system directories.  */
		  if (__glibc_unlikely (l->l_flags_1 & DF_1_NODEFLIB))
		    {
		      const char *dirp = system_dirs;
		      unsigned int cnt = 0;
		      do
			{
			  if (memcmp (cached[index], dirp,
			              system_dirs_len[cnt]) == 0)
			    {
			      use_candidate = false;
			      break;
			    }
			  dirp += system_dirs_len[cnt] + 1;
			  ++cnt;
			}
		      while (cnt < nsystem_dirs_len);
		    }

		  if (use_candidate)
		    {
		      if (__glibc_unlikely (GLRO(dl_debug_mask) & DL_DEBUG_LIBS))
			_dl_debug_printf ("  trying file=%s\n", cached[index]);

		      fd = open_verify (cached[index], -1,
					&fb,
					loader ?: GL(dl_ns)[nsid]._ns_loaded,
					LA_SER_CONFIG, mode,
					&found_other_class, false);
		      if (__glibc_likely (fd != -1))
			{
			  realname = cached[index];
			  cached[index] = NULL;
			  break;
			}
		    }
		}

	      for (size_t index = 0; cached[index] != NULL; ++index)
		free (cached[index]);
	      free (cached);
	    }
	}
#endif
'''
    replace_once(dl_load, old_cache_block, new_cache_block)

    replace_once(
        test,
        """  /* Remove the second override again, without running ldconfig.\n     Ideally, this would revert to implementation 2.  However, in the\n     current implementation, the cache returns exactly one file name\n     which does not exist after unlinking, so the dlopen fails.  */\n  xunlink (\"/glibc-test/lib/glibc-hwcaps/prepend3/\" SONAME);\n  TEST_VERIFY (dlopen (SONAME, RTLD_NOW) == NULL);\n""",
        """  /* Remove the preferred override without running ldconfig.  Cache\n     lookup should continue with the next compatible cached candidate.  */\n  xunlink (\"/glibc-test/lib/glibc-hwcaps/prepend3/\" SONAME);\n  {\n    void *handle = xdlopen (SONAME, RTLD_NOW);\n    int (*marker1) (void) = xdlsym (handle, \"marker1\");\n    TEST_COMPARE (marker1 (), 2);\n    xdlclose (handle);\n  }\n""",
    )

    print("classification\tcandidate_transform_applied")


if __name__ == "__main__":
    main()
