#!/usr/bin/env python3
from pathlib import Path

vm_config = Path("vmm/src/vm_config.rs")
vm_text = vm_config.read_text()
if "validate_tdx" in vm_text:
    raise SystemExit("TDX payload candidate already present in vm_config.rs")

old_method = '''impl PayloadConfig {
    /// Validates the payload config.
    ///
    /// Succeeds if Cloud Hypervisor will be able to boot the configuration.
    /// Further, warns for some odd configurations.
    pub fn validate(&mut self) -> Result<(), PayloadConfigError> {
        #[cfg(feature = "igvm")]
        {
            if self.igvm.is_some() {
                if self.firmware.is_some() {
                    return Err(PayloadConfigError::IgvmPlusOtherPayloads);
                }
                return Ok(());
            }
        }
        match (&self.firmware, &self.kernel) {
            (Some(_firmware), Some(_kernel)) => Err(PayloadConfigError::FirmwarePlusOtherPayloads),
            (Some(_firmware), None) => {
                if self.cmdline.is_some() {
                    warn!("Ignoring cmdline parameter as firmware is provided as the payload");
                    self.cmdline = None;
                }
                if self.initramfs.is_some() {
                    warn!("Ignoring initramfs parameter as firmware is provided as the payload");
                    self.initramfs = None;
                }
                Ok(())
            }
            (None, Some(_kernel)) => Ok(()),
            (None, None) => Err(PayloadConfigError::MissingBootitem),
        }?;

        #[cfg(feature = "fw_cfg")]
        if let Some(fw_cfg_config) = &self.fw_cfg_config {
            fw_cfg_config.validate(self)?;
        }

        Ok(())
    }
}
'''
new_method = '''impl PayloadConfig {
    /// Validates the payload config.
    ///
    /// Succeeds if Cloud Hypervisor will be able to boot the configuration.
    /// Further, warns for some odd configurations.
    pub fn validate(&mut self) -> Result<(), PayloadConfigError> {
        self.validate_inner(false)
    }

    #[cfg(feature = "tdx")]
    pub(crate) fn validate_tdx(&mut self) -> Result<(), PayloadConfigError> {
        self.validate_inner(true)
    }

    fn validate_inner(&mut self, tdx_direct_kernel: bool) -> Result<(), PayloadConfigError> {
        #[cfg(feature = "igvm")]
        {
            if self.igvm.is_some() {
                if self.firmware.is_some() {
                    return Err(PayloadConfigError::IgvmPlusOtherPayloads);
                }
                return Ok(());
            }
        }
        match (&self.firmware, &self.kernel) {
            (Some(_firmware), Some(_kernel)) if tdx_direct_kernel => {
                if self.initramfs.is_some() {
                    warn!("Ignoring initramfs parameter as TDX firmware does not consume it");
                    self.initramfs = None;
                }
                Ok(())
            }
            (Some(_firmware), Some(_kernel)) => Err(PayloadConfigError::FirmwarePlusOtherPayloads),
            (Some(_firmware), None) => {
                if !tdx_direct_kernel && self.cmdline.is_some() {
                    warn!("Ignoring cmdline parameter as firmware is provided as the payload");
                    self.cmdline = None;
                }
                if self.initramfs.is_some() {
                    warn!("Ignoring initramfs parameter as firmware is provided as the payload");
                    self.initramfs = None;
                }
                Ok(())
            }
            (None, Some(_kernel)) => Ok(()),
            (None, None) => Err(PayloadConfigError::MissingBootitem),
        }?;

        #[cfg(feature = "fw_cfg")]
        if let Some(fw_cfg_config) = &self.fw_cfg_config {
            fw_cfg_config.validate(self)?;
        }

        Ok(())
    }
}
'''
if vm_text.count(old_method) != 1:
    raise SystemExit("unexpected PayloadConfig::validate method shape")
vm_config.write_text(vm_text.replace(old_method, new_method, 1))

config = Path("vmm/src/config.rs")
text = config.read_text()
old_validation = '''        // Is the payload configuration bootable?
        self.payload
            .as_mut()
            .ok_or(ValidationError::PayloadError(
                PayloadConfigError::MissingBootitem,
            ))?
            .validate()?;

        #[cfg(feature = "tdx")]
        {
            let tdx_enabled = self.platform.as_ref().is_some_and(|p| p.tdx);
            // At this point we know payload isn't None.
            if tdx_enabled && self.payload.as_ref().unwrap().firmware.is_none() {
                return Err(ValidationError::TdxFirmwareMissing);
            }
'''
new_validation = '''        #[cfg(feature = "tdx")]
        let tdx_enabled = self.platform.as_ref().is_some_and(|p| p.tdx);

        // Is the payload configuration bootable?
        let payload = self
            .payload
            .as_mut()
            .ok_or(ValidationError::PayloadError(
                PayloadConfigError::MissingBootitem,
            ))?;
        #[cfg(feature = "tdx")]
        if tdx_enabled {
            payload.validate_tdx()?;
        } else {
            payload.validate()?;
        }
        #[cfg(not(feature = "tdx"))]
        payload.validate()?;

        #[cfg(feature = "tdx")]
        {
            // At this point we know payload isn't None.
            if tdx_enabled && self.payload.as_ref().unwrap().firmware.is_none() {
                return Err(ValidationError::TdxFirmwareMissing);
            }
'''
if text.count(old_validation) != 1:
    raise SystemExit("unexpected VmConfig payload/TDX validation ordering")
config.write_text(text.replace(old_validation, new_validation, 1))
