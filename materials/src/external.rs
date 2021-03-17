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

fn exec_branch(item_qty: (Item, u64), inv: Inventory, branch: &Branch) -> (Inventory, Strategy) {
    return (Inventory::new(), Strategy::from(vec![Action::Terminate(true)]))
    // let mut strat = Strategy::new(None);
    // match branch {
    //     Branch::Trade => {
    //         for (item, _) in rec.non_zero() {
    //             let Item(class, _, _) = item;
    //             (inv, s1) = inv.migrate_all(&class, 0, area); // free trades only
    //             _strat = _strat.extend(s1)
    //         }
    //         strat
    //     },
    //     Branch::Dismantle => {
    //
    //         strat
    //     }
    // };
    // return (rec, inv, strat)
}

/// Find a strategy to construct the recipe from the provided inventory.
///
/// A Strategy represents the set of actions required to make the translation
/// from one Inventory to another. Strategies consist of a series of actions
/// which end in Action::Terminate(success: bool). Each Action has an associated
/// cost, and thus Strategies can be compared cost wise.
///
/// To progress from one Inventory to a target Inventory, there are three
/// possible branches of logic which could potentially advance you to your goal:
/// 1. Perform Zero-Cost Trades:
///     You may have enough materials to build the recipe if you do some trades first.
///     The difficulty here is that to perform trades, materials must be the base of
///     their Class, so you must first Dismantle to Trade. Because of this, trading
///     is not necessary a free action.
/// 2. Perform Downgrades:
///     It may be necessary to break down materials into lower level materials. This
///     costs 20% of the value of higher tier material, so this has a cost associated
///     with it. It should be noted that dismantling higher tiers SHOULD have a higher
///     associated cost, but for a first pass implementation, this detail will be
///     elided, with the result being sub-optimal Strategies may win.
/// 3. Perform Upgrades:
///     There is no associated cost to the Upgrade action. This is sound as long as
///     the result of any Upgrade is actually used in the recipe.
pub fn find_strategy(recipe: Inventory, inventory: Inventory, area: TradeArea) -> Strategy {
    if inventory >= recipe {
        return Strategy::from(vec![Action::Terminate(true)])
    }
    let mut invs = [inventory.clone(), inventory.clone(), inventory.clone()];
    let mut strats = [Strategy::new(), Strategy::new(), Strategy::new()];
    for (item, amount) in recipe.non_zero() {
        let mut _s = [Strategy::new(), Strategy::new(), Strategy::new()];
        for (i, branch) in [Branch::Trade, Branch::Upgrade, Branch::Dismantle].iter().enumerate() {
            (invs[i], _s[i]) = exec_branch((item, amount), inventory.clone(), branch);
            strats[i] = strats[i].clone().concat(_s[i].clone())
        }
    }
    for i in 0..strats.len() {
        if !strats[i].terminal() {
            strats[i] = strats[i].clone().concat(find_strategy(recipe, invs[i], area));
        }
    }
    strats.iter().min().unwrap().clone()
}


#[test]
fn test_find_strategy_terminates() {
    find_strategy(Inventory::new(), Inventory::new(), TradeTable::A1);

    let mut recipe = Inventory::new();
    let mut inv = Inventory::new();
    recipe = recipe.adjustment(&Name::WoodenLog, 10);
    inv = inv.adjustment(&Name::WoodenLog, 0);
    find_strategy(recipe, inv, TradeTable::A1);
}
