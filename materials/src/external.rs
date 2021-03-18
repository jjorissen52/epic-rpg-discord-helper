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

fn exec_branch(item_qty: (Item, u64), mut inv: Inventory, branch: &Branch, area: TradeArea) -> (u64, Inventory, Strategy) {
    let (item, starting_qty) = item_qty;
    let mut recipe_amount = starting_qty;
    let Item(desired_class, desired_name, _) = item;
    match branch {
        Branch::Trade => {
            let mut strat = Strategy::new();
            let gaining = Items[Items::first_of(&desired_class)].1;
            let tradeable = [&Name::WoodenLog, &Name::NormieFish, &Name::Apple, &Name::Ruby];
            for losing in tradeable.iter() {
                if recipe_amount == 0 {
                    strat = strat.add(Action::Terminate(true));
                    break
                }
                inv = inv.trade(losing, &gaining, recipe_amount as i128, area);
                let gained = inv.get_item(&gaining);
                if gained.1 != 0 {
                    let adjustment = min(recipe_amount, gained.1);
                    recipe_amount -= adjustment;
                    inv = inv.adjustment(&gaining, -(adjustment as i128));
                    strat = strat.add(Action::Trade)
                }
            }
            let recipe_reduction = starting_qty - recipe_amount;
            if recipe_reduction == 0 {
                strat = strat.add(Action::Terminate(false));
            }
            (recipe_reduction, inv, strat)
        },
        Branch::Dismantle => (0, inv, Strategy::from(vec![Action::Terminate(false)])),
        Branch::Upgrade => (0, inv, Strategy::from(vec![Action::Terminate(false)])),
    }
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
    let mut recs = [recipe.clone(), recipe.clone(), recipe.clone()];
    let mut strats = [Strategy::new(), Strategy::new(), Strategy::new()];
    for (item, amount) in recipe.non_zero() {
        let Item(_, name, _) = item;
        let mut _s = [Strategy::new(), Strategy::new(), Strategy::new()];
        let mut reduction = 0;
        for (i, branch) in [Branch::Trade, Branch::Upgrade, Branch::Dismantle].iter().enumerate() {
            (reduction, invs[i], _s[i]) = exec_branch((item, amount), inventory.clone(), branch, area);
            recs[i] = recs[i].adjustment(&name, -(reduction as i128));
            strats[i] = strats[i].clone().concat(_s[i].clone())
        }
    }
    for i in 0..strats.len() {
        if !strats[i].terminal() {
            strats[i] = strats[i].clone().concat(find_strategy(recs[i], invs[i], area));
        }
    }
    strats.iter().min().unwrap().clone()
}

pub fn can_craft(recipe: Inventory, inventory: Inventory, area: TradeArea) -> bool {
    let actions = find_strategy(recipe, inventory, area).into_vec();
    if let Action::Terminate(success) = actions[actions.len() - 1] {
        return success
    }
    panic!("Not possible; all strategies must have terminated to get here.")
}


#[test]
fn test_find_strategy_terminates() {
    find_strategy(Inventory::new(), Inventory::new(), TradeTable::A1);

    let recipe = Inventory::from(vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from(vec![(&Name::WoodenLog, 0)]);
    find_strategy(recipe, inv, TradeTable::A1);
}

#[test]
fn test_can_craft_with_trades() {
    let recipe = Inventory::from(vec![(&Name::NormieFish, 10)]);
    let inv = Inventory::from(vec![(&Name::WoodenLog, 10)]);
    assert!(can_craft(recipe.clone(), inv.clone(), TradeTable::A1));
    assert!(!can_craft(recipe.clone(), inv.clone(), TradeTable::A10));

    let recipe = Inventory::from(vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from(vec![(&Name::Apple, 2)]);
    assert!(can_craft(recipe.clone(), inv.clone(), TradeTable::A6));
    assert!(!can_craft(recipe.clone(), inv.clone(), TradeTable::A3));
}
