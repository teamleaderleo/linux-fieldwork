use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let mut args = env::args_os().skip(1);
    let program = args.next().expect("program argument");
    let cwd = PathBuf::from(args.next().expect("cwd argument"));
    let marker = PathBuf::from(args.next().expect("marker output argument"));
    let launch_record = PathBuf::from(args.next().expect("launch record argument"));
    assert!(args.next().is_none(), "unexpected extra arguments");

    let _ = fs::remove_file(&marker);
    let result = Command::new(&program)
        .current_dir(&cwd)
        .env("PROBE_RESULT", &marker)
        .status();

    let record = match result {
        Ok(status) => format!(
            "spawn=ok\nstatus={}\nprogram={}\ncwd={}\nmarker_exists={}\n",
            status,
            PathBuf::from(program).display(),
            cwd.display(),
            marker.is_file(),
        ),
        Err(error) => format!(
            "spawn=error\nerror_kind={:?}\nerror={}\nprogram={}\ncwd={}\nmarker_exists={}\n",
            error.kind(),
            error,
            PathBuf::from(program).display(),
            cwd.display(),
            marker.is_file(),
        ),
    };
    fs::write(launch_record, record).expect("write launch record");
}
