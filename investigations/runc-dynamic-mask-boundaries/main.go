package main

import (
	"errors"
	"fmt"
	"math/bits"
	"os"
	"runtime"
	"unsafe"

	"golang.org/x/sys/unix"
)

const acceptedMaxID = 64 * 1024

func constructorProbe() error {
	exclusive := unix.NewCPUSet(acceptedMaxID)
	exclusive.Fill()
	inclusive := unix.NewCPUSet(acceptedMaxID + 1)
	inclusive.Fill()

	fmt.Printf(
		"constructor arch=%s word_bits=%d accepted_max_id=%d exclusive_words=%d exclusive_has_max=%t inclusive_words=%d inclusive_has_max=%t\n",
		runtime.GOARCH,
		bits.UintSize,
		acceptedMaxID,
		len(exclusive),
		exclusive.IsSet(acceptedMaxID),
		len(inclusive),
		inclusive.IsSet(acceptedMaxID),
	)

	if exclusive.IsSet(acceptedMaxID) {
		return errors.New("exclusive NewCPUSet bound unexpectedly contains the accepted top ID")
	}
	if !inclusive.IsSet(acceptedMaxID) {
		return errors.New("inclusive NewCPUSet bound does not contain the accepted top ID")
	}
	return nil
}

func nodeMask(node int) unix.CPUSetDynamic {
	mask := unix.NewCPUSet(node + 1)
	mask.Set(node)
	return mask
}

func wrapperProbe(node int) {
	mask := nodeMask(node)
	err := unix.SetMemPolicyDynamic(unix.MPOL_BIND, mask)
	fmt.Printf(
		"wrapper arch=%s word_bits=%d words=%d bytes=%d requested_node=%d result=%v\n",
		runtime.GOARCH,
		bits.UintSize,
		len(mask),
		len(mask)*(bits.UintSize/8),
		node,
		err,
	)
}

func rawProbe(node int, plusOne bool) {
	mask := nodeMask(node)
	maxnode := len(mask) * bits.UintSize
	if plusOne && maxnode != 0 {
		maxnode++
	}
	var maskPointer unsafe.Pointer
	if len(mask) > 0 {
		maskPointer = unsafe.Pointer(&mask[0])
	}

	_, _, errno := unix.Syscall(
		unix.SYS_SET_MEMPOLICY,
		uintptr(unix.MPOL_BIND),
		uintptr(maskPointer),
		uintptr(maxnode),
	)

	var err error
	if errno != 0 {
		err = errno
	}
	fmt.Printf(
		"raw arch=%s word_bits=%d words=%d maxnode=%d plus_one=%t requested_node=%d result=%v\n",
		runtime.GOARCH,
		bits.UintSize,
		len(mask),
		maxnode,
		plusOne,
		node,
		err,
	)
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage: probe constructor|wrapper|raw|raw-plus-one|all")
}

func main() {
	if len(os.Args) != 2 {
		usage()
		os.Exit(2)
	}

	switch os.Args[1] {
	case "constructor":
		if err := constructorProbe(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	case "wrapper":
		wrapperProbe(7)
	case "raw":
		rawProbe(7, false)
	case "raw-plus-one":
		rawProbe(7, true)
	case "all":
		if err := constructorProbe(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		wrapperProbe(7)
		rawProbe(7, false)
		rawProbe(7, true)
	default:
		usage()
		os.Exit(2)
	}
}
