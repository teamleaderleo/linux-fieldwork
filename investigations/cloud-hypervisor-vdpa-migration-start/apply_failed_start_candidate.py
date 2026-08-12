#!/usr/bin/env python3
from pathlib import Path

path = Path("virtio-devices/src/vdpa.rs")
text = path.read_text()
old = '''impl Migratable for Vdpa {
    fn start_migration(&mut self) -> result::Result<(), MigratableError> {
        self.migrating = true;
        // Given there's no way to track dirty pages, we must suspend the
        // device as soon as the migration process starts.
        if self.backend_features & (1 << VHOST_BACKEND_F_SUSPEND) != 0 {
            assert!(self.vhost.is_some());
            self.vhost.as_ref().unwrap().suspend().map_err(|e| {
                MigratableError::StartMigration(anyhow!("Error suspending vDPA device: {e:?}"))
            })
        } else {
            Err(MigratableError::StartMigration(anyhow!(
                "vDPA device can't be suspended"
            )))
        }
    }
'''
new = '''impl Migratable for Vdpa {
    fn start_migration(&mut self) -> result::Result<(), MigratableError> {
        // Given there's no way to track dirty pages, we must suspend the
        // device as soon as the migration process starts.
        if self.backend_features & (1 << VHOST_BACKEND_F_SUSPEND) != 0 {
            assert!(self.vhost.is_some());
            self.vhost.as_ref().unwrap().suspend().map_err(|e| {
                MigratableError::StartMigration(anyhow!("Error suspending vDPA device: {e:?}"))
            })?;
            self.migrating = true;
            Ok(())
        } else {
            Err(MigratableError::StartMigration(anyhow!(
                "vDPA device can't be suspended"
            )))
        }
    }
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one vDPA start_migration owner in {path}, found {count}")
path.write_text(text.replace(old, new, 1))
