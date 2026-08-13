#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/config.rs")
text = path.read_text()
marker = "tdx_firmware_kernel_is_rejected_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod tests {"
if text.count(anchor) != 1:
    raise SystemExit("unexpected config unit-test anchor count")

probe = r'''#[cfg(test)]
mod tdx_payload_validation_probe_tests {
    use super::*;

    #[cfg(feature = "tdx")]
    fn config(tdx: bool, kernel: bool, cmdline: bool) -> VmConfig {
        let kernel_field = if kernel {
            r#", "kernel": "/tmp/bzImage""#
        } else {
            ""
        };
        let cmdline_field = if cmdline {
            r#", "cmdline": "console=hvc0 root=/dev/vda""#
        } else {
            ""
        };
        let json = format!(
            r#"{{
                "payload": {{
                    "firmware": "/tmp/tdshim"{kernel_field}{cmdline_field}
                }},
                "platform": {{ "tdx": {tdx} }}
            }}"#
        );
        serde_json::from_str(&json).unwrap()
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdx_firmware_kernel_is_rejected_baseline() {
        let mut config = config(true, true, true);
        let result = config.validate();
        println!("TDX_PAYLOAD_VALIDATION_BASELINE kernel_result={result:?}");
        assert!(result.is_err());
        assert!(format!("{result:?}").contains("FirmwarePlusOtherPayloads"));
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdx_firmware_cmdline_is_silently_removed_baseline() {
        let mut config = config(true, false, true);
        let result = config.validate();
        let cmdline = config.payload.as_ref().unwrap().cmdline.clone();
        println!(
            "TDX_PAYLOAD_VALIDATION_BASELINE cmdline_result={result:?} cmdline_after={cmdline:?}"
        );
        assert!(result.is_ok());
        assert!(cmdline.is_none());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn non_tdx_firmware_kernel_remains_rejected_control() {
        let mut config = config(false, true, true);
        let result = config.validate();
        println!("TDX_PAYLOAD_VALIDATION_CONTROL non_tdx_kernel={result:?}");
        assert!(result.is_err());
        assert!(format!("{result:?}").contains("FirmwarePlusOtherPayloads"));
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn non_tdx_firmware_cmdline_is_removed_control() {
        let mut config = config(false, false, true);
        let result = config.validate();
        let cmdline = config.payload.as_ref().unwrap().cmdline.clone();
        println!(
            "TDX_PAYLOAD_VALIDATION_CONTROL non_tdx_cmdline={result:?} cmdline_after={cmdline:?}"
        );
        assert!(result.is_ok());
        assert!(cmdline.is_none());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_firmware_kernel_should_validate() {
        let mut config = config(true, true, true);
        let result = config.validate();
        println!("TDX_PAYLOAD_VALIDATION_INVARIANT kernel_result={result:?}");
        assert!(
            result.is_ok(),
            "TDX firmware plus kernel is an intended direct-kernel boot mode"
        );
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_firmware_cmdline_should_be_preserved() {
        let mut config = config(true, false, true);
        let result = config.validate();
        let cmdline = config.payload.as_ref().unwrap().cmdline.clone();
        println!(
            "TDX_PAYLOAD_VALIDATION_INVARIANT cmdline_result={result:?} cmdline_after={cmdline:?}"
        );
        assert!(result.is_ok());
        assert_eq!(cmdline.as_deref(), Some("console=hvc0 root=/dev/vda"));
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
