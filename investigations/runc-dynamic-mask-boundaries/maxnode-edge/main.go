package main

import (
	"errors"
	"fmt"
	"math/bits"
	"os"
	"unsafe"

	"golang.org/x/sys/unix"
)

func setRelativeBind(mask []uintptr, maxnode uintptr) error {
	var pointer unsafe.Pointer
	if len(mask) != 0 {
		pointer = unsafe.Pointer(&mask[0])
	}
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

func main() {
	if bits.UintSize != 64 {
		fmt.Fprintf(os.Stderr, "this discriminator currently expects 64-bit unsigned long, got %d\n", bits.UintSize)
		os.Exit(77)
	}

	// Set only bit 63. Linux MPOL_F_RELATIVE_NODES folds a non-empty
	// user mask onto the task's currently allowed memory nodes. This lets
	// an ordinary small machine distinguish whether maxnode includes the
	// final bit without requiring a real node 63.
	mask := []uintptr{uintptr(1) << 63}

	err64 := setRelativeBind(mask, 64)
	if err64 == nil {
		if err := resetPolicy(); err != nil {
			fmt.Fprintf(os.Stderr, "reset after maxnode=64: %v\n", err)
			os.Exit(1)
		}
	}

	err65 := setRelativeBind(mask, 65)
	if err65 == nil {
		if err := resetPolicy(); err != nil {
			fmt.Fprintf(os.Stderr, "reset after maxnode=65: %v\n", err)
			os.Exit(1)
		}
	}

	fmt.Printf("word_bits\t%d\n", bits.UintSize)
	fmt.Printf("highest_set_bit\t63\n")
	fmt.Printf("maxnode_64\t%v\n", err64)
	fmt.Printf("maxnode_65\t%v\n", err65)

	if !errors.Is(err64, unix.EINVAL) {
		fmt.Fprintf(os.Stderr, "maxnode=64 returned %v, want EINVAL for the dropped final bit\n", err64)
		os.Exit(1)
	}
	if err65 != nil {
		fmt.Fprintf(os.Stderr, "maxnode=65 returned %v, want success for the included relative bit\n", err65)
		os.Exit(1)
	}

	fmt.Println("classification\tbits_plus_one_includes_final_bit")
}
