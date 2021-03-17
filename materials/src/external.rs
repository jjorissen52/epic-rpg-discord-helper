use crate::crafting::{Items, Item, Inventory, Strategy, Class, Action, Name, TradeTable, TradeArea};
use std::cmp::min;

pub fn future_logs(
    area: usize,
    wooden_log: u64, epic_log: u64, super_log: u64, mega_log: u64, hyper_log: u64, ultra_log: u64,
    normie_fish: u64, golden_fish: u64, epic_fish: u64,
    apple: u64, banana: u64,
    ruby: u64,
) -> Option<u64> {
    let inv = Inventory::itemized(
        wooden_log, epic_log, super_log, mega_log, hyper_log, ultra_log,
        normie_fish, golden_fish, epic_fish,
        apple, banana,
        ruby
    );
    if let Some(area) = TradeTable::from_usize(area) {
        return Some(inv.future(area, TradeTable::A10).get_qty(&Name::WoodenLog))
    };
    None
}

#[test]
fn test_future() {
    let res = future_logs(
        2,
        100_000, 0, 0, 0, 0, 0,
        0, 0, 0,
        0, 0, 0
    ).unwrap();
    assert_eq!(res, 1_687_500);
}

enum Branch {
    Trade,
    Upgrade,
    Dismantle,
}

// fn exec_strategy(mut rec: Inventory, mut inv: Inventory, branch: Branch, area: TradeArea) -> Strategy {
//     let mut strat = Strategy::new(None);
//     match branch {
//         Branch::Trade => {
//             for (item, _) in rec.non_zero() {
//                 let Item(class, _, _) = item;
//                 (inv, s1) = inv.migrate_all(&class, max_steps, area);
//                 _strat = _strat.extend(s1)
//             }
//             strat
//         },
//         Branch::Upgrade => {
//             for (ritem, rqty) in rec.non_zero() {
//                 let Item(rclass, ritem, _) = ritem;
//                 for (iitem, iqty) in inv.non_zero() {
//                     let Item(iclass, iname, _) = iitem;
//                     (inv, s1) = inv.migrate_all(&class, max_steps, area);
//                     _strat = _strat.extend(s1)
//                 }
//             }
//             strat
//         }
//     }
//
// }
//
//
// pub fn find_strategy(recipe: Inventory, inventory: Inventory, area: TradeArea) -> Strategy {
//     if recipe > inventory {
//         return Strategy::new(Some(Action::Terminate(true)))
//     }
//     let mut s1 = Strategy::new(None); let mut s2; let mut s3;
//     let (mut r1, mut i1) = (recipe.clone(), inventory.clone());
//     let (mut r2, mut i2) = (recipe.clone(), inventory.clone());
//     let (mut r3, mut i3) = (recipe.clone(), inventory.clone());
//
//     // calculate new recipe and inventory
//     // first we try trading
//     match
//     for (ritem, ramount) in r1.non_zero() {
//         let Item(rclass, _, _) = ritem;
//         for (iitem, iamount) in i1.non_zero() {
//             let Item(iclass, _, _) = iitem;
//             (i1, s1) = i1.migrate_all(&rclass, max_steps, area)
//         }
//     }
//
//     // explore new branches
//     return min(
//         min(
//             find_strategy(r1, i1, area),
//             find_strategy(r2, i2, area),
//             ),
//             find_strategy(r2, i2, area),
//     )
// }
