/*
 * Minimal source fixture retaining the exact util-linux v2.41
 * ul_path_cpuparse() error-path text needed to verify the canonical patch.
 * The upstream lib/path.c file declares its source public domain.
 */

static int ul_path_cpuparse(void)
{
	int rc = 0;
	void **set = 0;
	void *buf = 0;

	rc = 0;

out:
	if (rc)
		cpuset_free(*set);
	free(buf);
	return rc;
}
