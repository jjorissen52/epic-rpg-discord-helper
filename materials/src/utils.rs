use std::path::Path;
use std::fs::{File, OpenOptions};
use std::io::Write;
use core::cmp::PartialOrd;

pub fn clamp<T: PartialOrd>(input: T, min: T, max: T) -> T {
    debug_assert!(min <= max, "min must be less than or equal to max");
    if input < min {
        min
    } else if input > max {
        max
    } else {
        input
    }
}

pub fn write(line: String) {
    let path = Path::new("dbg.txt");
    let display = path.display();

    // Open the path in read-only mode, returns `io::Result<File>`
    let mut file = match OpenOptions::new()
        .append(true)
        .create(true)
        .open(&path) {
        Err(why) => panic!("couldn't open {}: {}", display, why),
        Ok(file) => file,
    };

    // Write the `LOREM_IPSUM` string to `file`, returns `io::Result<()>`
    file.write_all(line.as_bytes());
}
