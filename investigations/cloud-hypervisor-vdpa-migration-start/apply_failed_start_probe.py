#!/usr/bin/env python3
from pathlib import Path

path = Path("virtio-devices/src/vdpa.rs")
text = path.read_text()
marker = "failed_start_migration_keeps_normal_runtime_state"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

probe = r'''#[cfg(test)]
mod unit_tests {
    use super::*;

    fn vdpa_without_suspend_support() -> Vdpa {
        Vdpa {
            common: VirtioCommon::default(),
            id: "test-vdpa".to_owned(),
            vhost: None,
            iova_range: VhostVdpaIovaRange {
                first: 0,
                last: u64::MAX,
            },
            enabled_queues: BTreeMap::new(),
            backend_features: 0,
            migrating: false,
        }
    }

    #[test]
    fn failed_start_migration_keeps_normal_runtime_state() {
        let mut vdpa = vdpa_without_suspend_support();

        vdpa.start_migration().unwrap_err();

        assert!(
            !vdpa.migrating,
            "failed start_migration must not authorize migration-only behavior"
        );
        assert!(vdpa.pause().is_err());
    }
}'''

path.write_text(text.rstrip() + "\n\n" + probe)