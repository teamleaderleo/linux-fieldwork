package main

import (
	"errors"
	"fmt"
	"math/bits"
	"os"
	"unsafe"

	"golang.org/x/sys/unix"
)

func setRelativeBindPointer(pointer unsafe.Pointer, maxnode uintptr) error {
	_, _, errno := unix.Syscall(
		unix.SYS_SET_MEMPOLICY,
		uintptr(unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES),
		uintptr(pointer),
		maxnode,
	)
	if errno != 0 {
		return errno
	}
	return nil
}

func setRelativeBind(mask []uintptr, maxnode uintptr) error {
	var pointer unsafe.Pointer
	if len(mask) != 0 {
		pointer = unsafe.Pointer(&mask[0])
	}
	return setRelativeBindPointer(pointer, maxnode)
}

func resetPolicy() error {
	_, _, errno := unix.Syscall(
		unix.SYS_SET_MEMPOLICY,
		uintptr(unix.MPOL_DEFAULT),
		0,
		0,
	)
	if errno != 0 {
		return errno
	}
	return nil
}

func resetAfterSuccess(label string, err error) {
	if err != nil {
		return
	}
	if resetErr := resetPolicy(); resetErr != nil {
		fmt.Fprintf(os.Stderr, "reset after %s: %v\n", label, resetErr)
		os.Exit(1)
	}
}

func main() {
	if bits.UintSize != 64 {
		fmt.Fprintf(os.Stderr, "this discriminator currently expects 64-bit unsigned long, got %d\n", bits.UintSize)
		os.Exit(77)
	}

	// Dynamic case: set only bit 63. MPOL_F_RELATIVE_NODES folds a
	// non-empty user mask onto the task's currently allowed memory nodes.
	// This lets an ordinary small machine distinguish whether maxnode
	// includes the final bit without requiring a real node 63.
	dynamicMask := []uintptr{uintptr(1) << 63}
	err64 := setRelativeBind(dynamicMask, 64)
	resetAfterSuccess("dynamic maxnode=64", err64)
	err65 := setRelativeBind(dynamicMask, 65)
	resetAfterSuccess("dynamic maxnode=65", err65)

	fmt.Printf("word_bits\t%d\n", bits.UintSize)
	fmt.Printf("dynamic_highest_set_bit\t63\n")
	fmt.Printf("dynamic_maxnode_64\t%v\n", err64)
	fmt.Printf("dynamic_maxnode_65\t%v\n", err65)

	if !errors.Is(err64, unix.EINVAL) {
		fmt.Fprintf(os.Stderr, "dynamic maxnode=64 returned %v, want EINVAL for the dropped final bit\n", err64)
		os.Exit(1)
	}
	if err65 != nil {
		fmt.Fprintf(os.Stderr, "dynamic maxnode=65 returned %v, want success for the included relative bit\n", err65)
		os.Exit(1)
	}

	// Fixed CPUSet case: current x/sys passes _CPU_SETSIZE (1024). Set
	// only bit 1023 so the same final-bit convention is observable. The
	// raw 1025 control is allowed to report EINVAL on kernels whose
	// configured MAX_NUMNODES is smaller than 1024; when it succeeds, the
	// hosted kernel can directly distinguish the fixed wrapper edge too.
	var fixed unix.CPUSet
	fixed.Set(1023)
	fixedWrapperErr := unix.SetMemPolicy(
		unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES,
		&fixed,
	)
	resetAfterSuccess("fixed wrapper", fixedWrapperErr)
	fixedRaw1025Err := setRelativeBindPointer(unsafe.Pointer(&fixed), 1025)
	resetAfterSuccess("fixed raw maxnode=1025", fixedRaw1025Err)

	fmt.Printf("fixed_highest_set_bit\t1023\n")
	fmt.Printf("fixed_wrapper_maxnode_1024\t%v\n", fixedWrapperErr)
	fmt.Printf("fixed_raw_maxnode_1025\t%v\n", fixedRaw1025Err)

	if !errors.Is(fixedWrapperErr, unix.EINVAL) {
		fmt.Fprintf(os.Stderr, "fixed wrapper returned %v, want EINVAL when bit 1023 is dropped\n", fixedWrapperErr)
		os.Exit(1)
	}
	if fixedRaw1025Err == nil {
		fmt.Println("fixed_classification\tfixed_wrapper_drops_final_bit")
	} else {
		fmt.Println("fixed_classification\thost_cannot_distinguish_fixed_final_bit")
	}

	fmt.Println("classification\tbits_plus_one_includes_final_bit")
}
