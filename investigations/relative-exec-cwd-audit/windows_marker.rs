use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let output = env::var_os("PROBE_RESULT")
        .map(PathBuf::from)
        .expect("PROBE_RESULT must name the marker output file");
    let executable = env::current_exe().expect("current executable path");
    fs::write(output, format!("{}\n", executable.display()))
        .expect("write executable identity marker");
}
