use crate::crafting::{Items, Item, Inventory, Strategy, Class, Action, Name, TradeTable, TradeArea};
use std::cmp::min;

pub fn future_logs(
    area: usize,
    wooden_log: u64, epic_log: u64, super_log: u64, mega_log: u64, hyper_log: u64, ultra_log: u64,
    normie_fish: u64, golden_fish: u64, epic_fish: u64,
    apple: u64, banana: u64,
    ruby: u64,
) -> Option<u64> {
    let _area = match TradeTable::from_usize(area) {
        Some(_area) => _area,
        None => return None,
    };
    Some(Inventory::itemized(
        _area,
        wooden_log, epic_log, super_log, mega_log, hyper_log, ultra_log,
        normie_fish, golden_fish, epic_fish,
        apple, banana,
        ruby
    ).future(TradeTable::A10)[&Name::WoodenLog])
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

fn exec_branch(recipe_qty: (Item, u64), mut inv: Inventory, branch: &Branch) -> (u64, Inventory, Strategy) {
    let (item, starting_qty) = recipe_qty;
    let mut recipe_amount = starting_qty;
    let Item(desired_class, desired_name, _) = item;
    match branch {
        Branch::Trade => {
            // perform any free trades into the current recipe item's class
            let mut strat = Strategy::new();
            let gaining = Items[Items::first_of(&desired_class)].1;
            let tradeable = [&Name::WoodenLog, &Name::NormieFish, &Name::Apple, &Name::Ruby];
            for losing in tradeable.iter() {
                if recipe_amount == 0 {
                    strat = strat.add(Action::Terminate(true));
                    break
                }
                inv = inv.trade(losing, &gaining, recipe_amount as i128);
                let gained = inv[&gaining];
                if gained != 0 {
                    let adjustment = min(recipe_amount, gained);
                    recipe_amount -= adjustment;
                    inv[&gaining] -= adjustment;
                    strat = strat.add(Action::Trade)
                }
            }
            let recipe_reduction = starting_qty - recipe_amount;
            if recipe_reduction == 0 {
                strat = strat.add(Action::Terminate(false));
            }
            (recipe_reduction, inv, strat)
        },
        Branch::Dismantle => {
            // find next non-zero inventory item and dismantle from it to
            // the current recipe item
            let recipe_item_idx = Items::index_of(&desired_name);
            let mut idx = recipe_item_idx + 1;
            // Fruit just happens to be the last dismantle-able class
            // in Items::ITEMS
            let highest_idx = Items::last_of(&Class::Fruit);
            // Look for any items that could possibly be dismantled
            while idx <= highest_idx {
                let losing = inv[idx];
                if losing != 0 {
                    let (qty, remainder) = Items[idx]
                        .dismantle_to(losing, &desired_name, starting_qty);
                    // Subtract from the recipe cost either the quantity obtained from
                    // dismantling or the amount required, whichever is smallest.
                    // The rest of the items should be placed in the inventory.
                    let recipe_reduction = min(qty, starting_qty);
                    inv[idx] = remainder;
                    inv[recipe_item_idx] = qty - recipe_reduction;

                    // calculate the cost to record it in the strategy
                    let cost = Item::dismantle_cost(idx - 1, highest_idx, qty);
                    return (recipe_reduction, inv, Strategy::from(vec![Action::Dismantle(cost)]))
                }
                idx += 1;
            }
            // If we could not dismantle anything, this is not a necessary
            // part of a winning strategy.
            (0, inv, Strategy::from(vec![Action::Terminate(false)]))
        },
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
pub fn find_strategy(recipe: Inventory, inventory: Inventory) -> Strategy {
    if inventory >= recipe {
        return Strategy::from(vec![Action::Terminate(true)])
    }
    let mut invs = [inventory.clone(), inventory.clone(), inventory.clone()];
    let mut recs: [&mut Inventory; 3] = [&mut recipe.clone(), &mut recipe.clone(), &mut recipe.clone()];
    let mut strats = [Strategy::new(), Strategy::new(), Strategy::new()];
    for (item, amount) in recipe.non_zero() {
        let Item(_, name, _) = item;
        let mut _s = [Strategy::new(), Strategy::new(), Strategy::new()];
        let mut reduction = 0;
        for (i, branch) in [Branch::Trade, Branch::Upgrade, Branch::Dismantle].iter().enumerate() {
            (reduction, invs[i], _s[i]) = exec_branch((item, amount), inventory.clone(), branch);
            recs[i][&name] -= reduction;
            strats[i] = strats[i].clone().concat(_s[i].clone())
        }
    }
    for i in 0..strats.len() {
        if !strats[i].terminal() {
            strats[i] = strats[i].clone().concat(find_strategy(*recs[i], invs[i]));
        }
    }
    strats.iter().min().unwrap().clone()
}

pub fn can_craft(recipe: Inventory, inventory: Inventory) -> bool {
    let actions = find_strategy(recipe, inventory).into_vec();
    if let Action::Terminate(success) = actions[actions.len() - 1] {
        return success
    }
    panic!("Not possible; all strategies must have terminated to get here.")
}


#[test]
fn test_find_strategy_terminates() {
    find_strategy(Inventory::new(TradeTable::A1), Inventory::new(TradeTable::A1));

    let recipe = Inventory::from(TradeTable::A1, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from(TradeTable::A1, vec![(&Name::WoodenLog, 0)]);
    find_strategy(recipe, inv);
}

#[test]
fn test_can_craft_with_trades() {

    let recipe = Inventory::from(TradeTable::A1, vec![(&Name::NormieFish, 10)]);
    let inv = Inventory::from(TradeTable::A1, vec![(&Name::WoodenLog, 10)]);
    assert!(can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from(TradeTable::A10, vec![(&Name::NormieFish, 10)]);
    let inv = Inventory::from(TradeTable::A10, vec![(&Name::WoodenLog, 10)]);
    assert!(!can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from(TradeTable::A6, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from(TradeTable::A6, vec![(&Name::Apple, 2)]);
    assert!(can_craft(recipe.clone(), inv.clone()));

    // demonstrates a bug in the current implementation
    let recipe = Inventory::from(TradeTable::A3, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from(TradeTable::A3, vec![(&Name::Apple, 2)]);
    assert!(!can_craft(recipe.clone(), inv.clone()));
}

#[test]
fn test_can_craft_with_dismantles() {
    let recipe = Inventory::from(TradeTable::A6, vec![(&Name::NormieFish, 24)]);
    let inv = Inventory::from(TradeTable::A6, vec![(&Name::EpicFish, 2)]);

    assert!(can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from(TradeTable::A6, vec![(&Name::WoodenLog, 163_840)]);
    let inv = Inventory::from(TradeTable::A6, vec![(&Name::UltraLog, 2)]);
    assert!(can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from(TradeTable::A6, vec![(&Name::WoodenLog, 163_841)]);
    assert!(!can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from(TradeTable::A10, vec![(&Name::UltraLog, 1)]);
    let inv = Inventory::from(TradeTable::A10, vec![(&Name::Banana, 1)]);
    assert!(!can_craft(recipe.clone(), inv.clone()));
}

#[test]
fn test_can_craft_with_dismantles_and_trades() {
    // recipe equivalent of fish sword
    let recipe = Inventory::from(TradeTable::A1, vec![(&Name::NormieFish, 20*12), (&Name::WoodenLog, 20*5)]);
    let inv = Inventory::from(TradeTable::A1, vec![(&Name::EpicFish, 1)]);
    assert!(can_craft(recipe.clone(), inv.clone()));
}
