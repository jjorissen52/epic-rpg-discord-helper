#![allow(warnings)]
#![feature(destructuring_assignment)]

mod crafting;
mod tests;
mod external;
mod utils;

use pyo3::prelude::*;
use pyo3::{wrap_pyfunction, exceptions};

#[pyfunction]
pub fn future(
    area: usize,
    wooden_log: u64, epic_log: u64, super_log: u64, mega_log: u64, hyper_log: u64, ultra_log: u64,
    normie_fish: u64, golden_fish: u64, epic_fish: u64,
    apple: u64, banana: u64,
    ruby: u64,
) -> Result<u64, PyErr> {
    if let Some(logs) = external::future_logs(
        area,
        wooden_log, epic_log, super_log, mega_log, hyper_log, ultra_log,
        normie_fish, golden_fish, epic_fish,
        apple, banana,
        ruby
    ) {
        return Ok(logs)
    }
    Err(exceptions::PyValueError::new_err(format!("A{} is not a valid area!", area)))
}

#[pyfunction]
pub fn can_craft(
    recipe: [u64; 26],
    inventory: [u64; 26],
) -> bool {
   external::can_craft(recipe, inventory)
}

#[pymodule]
fn materials(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(future, m)?).unwrap();
    m.add_function(wrap_pyfunction!(can_craft, m)?).unwrap();
    m.add("INVENTORY_SIZE", crafting::Items::INV_SIZE);
    Ok(())
}
