package goarchiveprobe

import (
	"archive/tar"
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	archive "github.com/moby/go-archive"
	"github.com/moby/sys/user"
)

const expectedContent = "implied-parent-ok\n"

func archiveBytes(t *testing.T, explicitParent bool) []byte {
	t.Helper()

	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	writeDir := func(name string) {
		t.Helper()
		if err := tw.WriteHeader(&tar.Header{
			Name:     name,
			Typeflag: tar.TypeDir,
			Mode:     0o755,
		}); err != nil {
			t.Fatalf("write directory %q: %v", name, err)
		}
	}

	if explicitParent {
		writeDir("etc/")
	}
	writeDir("etc/dnf/")
	if err := tw.WriteHeader(&tar.Header{
		Name:     "etc/dnf/dnf.conf",
		Typeflag: tar.TypeReg,
		Mode:     0o644,
		Size:     int64(len(expectedContent)),
	}); err != nil {
		t.Fatalf("write file header: %v", err)
	}
	if _, err := tw.Write([]byte(expectedContent)); err != nil {
		t.Fatalf("write file payload: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("close tar writer: %v", err)
	}
	return buf.Bytes()
}

func runnerIdentityMapping() user.IdentityMapping {
	return user.IdentityMapping{
		UIDMaps: []user.IDMap{{ID: 0, ParentID: int64(os.Getuid()), Count: 1}},
		GIDMaps: []user.IDMap{{ID: 0, ParentID: int64(os.Getgid()), Count: 1}},
	}
}

func runUntar(t *testing.T, explicitParent bool) (string, error) {
	t.Helper()
	dest := t.TempDir()
	err := archive.Untar(
		bytes.NewReader(archiveBytes(t, explicitParent)),
		dest,
		&archive.TarOptions{
			NoLchown: true,
			IDMap:    runnerIdentityMapping(),
		},
	)
	if err != nil {
		return "", err
	}
	content, readErr := os.ReadFile(filepath.Join(dest, "etc", "dnf", "dnf.conf"))
	if readErr != nil {
		return "", fmt.Errorf("read extracted file: %w", readErr)
	}
	return string(content), nil
}

func TestExplicitParentControl(t *testing.T) {
	content, err := runUntar(t, true)
	if err != nil {
		t.Fatalf("explicit-parent control failed: %v", err)
	}
	if content != expectedContent {
		t.Fatalf("explicit-parent content = %q, want %q", content, expectedContent)
	}
}

func TestImpliedParentCompatibility(t *testing.T) {
	expect := os.Getenv("EXPECT_IMPLIED_PARENT")
	if expect != "pass" && expect != "fail" {
		t.Fatalf("EXPECT_IMPLIED_PARENT must be pass or fail, got %q", expect)
	}

	content, err := runUntar(t, false)
	t.Logf("EXPECT_IMPLIED_PARENT=%s error=%v content=%q", expect, err, content)

	if expect == "fail" {
		if err == nil {
			t.Fatalf("implied-parent extraction unexpectedly succeeded")
		}
		return
	}

	if err != nil {
		t.Fatalf("implied-parent extraction failed: %v", err)
	}
	if content != expectedContent {
		t.Fatalf("implied-parent content = %q, want %q", content, expectedContent)
	}
}
