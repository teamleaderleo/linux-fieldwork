package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"

	"github.com/opencontainers/cgroups"
)

type collectionShape struct {
	ResourcesNil bool `json:"resources_nil"`
	HugetlbNil   bool `json:"hugetlb_nil"`
	HugetlbLen   int  `json:"hugetlb_len"`
	UnifiedNil   bool `json:"unified_nil"`
	UnifiedLen   int  `json:"unified_len"`
}

type report struct {
	Dependency string                     `json:"dependency"`
	Mode       string                     `json:"mode"`
	Encoded    map[string]json.RawMessage `json:"encoded"`
	Shapes     map[string]collectionShape `json:"shapes"`
}

func nativeSamples() map[string]any {
	return map[string]any{
		"empty-cgroup": &cgroups.Cgroup{},
		"empty-resources": &cgroups.Cgroup{
			Resources: &cgroups.Resources{},
		},
		"empty-collections": &cgroups.Cgroup{
			Resources: &cgroups.Resources{
				HugetlbLimit: make([]*cgroups.HugepageLimit, 0),
				Unified:     map[string]string{},
			},
		},
		"nonzero-resources": &cgroups.Cgroup{
			Name: "probe",
			Resources: &cgroups.Resources{
				Memory:  1,
				Unified: map[string]string{"memory.high": "1"},
			},
		},
		"empty-stats": &cgroups.Stats{},
	}
}

func decodeSamples(encoded map[string]json.RawMessage) (map[string]any, error) {
	out := make(map[string]any, len(encoded))
	keys := make([]string, 0, len(encoded))
	for key := range encoded {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		var target any
		if key == "empty-stats" {
			target = &cgroups.Stats{}
		} else {
			target = &cgroups.Cgroup{}
		}
		if err := json.Unmarshal(encoded[key], target); err != nil {
			return nil, fmt.Errorf("decode %s: %w", key, err)
		}
		out[key] = target
	}
	return out, nil
}

func encodeSamples(samples map[string]any) (map[string]json.RawMessage, error) {
	out := make(map[string]json.RawMessage, len(samples))
	for key, value := range samples {
		dt, err := json.Marshal(value)
		if err != nil {
			return nil, fmt.Errorf("encode %s: %w", key, err)
		}
		out[key] = dt
	}
	return out, nil
}

func inspectShapes(samples map[string]any) map[string]collectionShape {
	out := map[string]collectionShape{}
	for key, value := range samples {
		cg, ok := value.(*cgroups.Cgroup)
		if !ok {
			continue
		}
		shape := collectionShape{ResourcesNil: cg.Resources == nil}
		if cg.Resources == nil {
			shape.HugetlbNil = true
			shape.UnifiedNil = true
		} else {
			shape.HugetlbNil = cg.HugetlbLimit == nil
			shape.HugetlbLen = len(cg.HugetlbLimit)
			shape.UnifiedNil = cg.Unified == nil
			shape.UnifiedLen = len(cg.Unified)
		}
		out[key] = shape
	}
	return out
}

func main() {
	dependency := os.Getenv("DEPENDENCY_LABEL")
	if dependency == "" {
		dependency = "unknown"
	}

	mode := "native"
	samples := nativeSamples()
	if len(os.Args) == 2 {
		mode = "decode"
		dt, err := os.ReadFile(os.Args[1])
		if err != nil {
			panic(err)
		}
		var input report
		if err := json.Unmarshal(dt, &input); err != nil {
			panic(err)
		}
		samples, err = decodeSamples(input.Encoded)
		if err != nil {
			panic(err)
		}
	} else if len(os.Args) != 1 {
		fmt.Fprintln(os.Stderr, "usage: serializer [report.json]")
		os.Exit(2)
	}

	encoded, err := encodeSamples(samples)
	if err != nil {
		panic(err)
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(report{
		Dependency: dependency,
		Mode:       mode,
		Encoded:    encoded,
		Shapes:     inspectShapes(samples),
	}); err != nil {
		panic(err)
	}
}
