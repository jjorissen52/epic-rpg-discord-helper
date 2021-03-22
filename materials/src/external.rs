use crate::crafting::{Items, Item, Inventory, Strategy, Class, Action, Name, TradeTable, TradeArea};
use std::cmp::min;
use std::collections::HashMap;

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
    ).log_value())
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

fn exec_branch(recipe_qty: (Item, u64), mut inv: Inventory, branch: &Branch) -> Vec<(u64, Strategy)> {
    let mut possible_strategies: Vec<(u64, Strategy)> = Vec::new();
    let (item, starting_qty) = recipe_qty;
    let mut recipe_amount = starting_qty;
    let Item(desired_class, desired_name, _) = item;
    match branch {
        Branch::Trade => {
            // perform any free trades into the current recipe item's class
            let mut actions: Vec<Action> = Vec::new();
            let gaining = Items[Items::first_of(&desired_class)].1;
            let tradeable = [&Name::WoodenLog, &Name::NormieFish, &Name::Apple, &Name::Ruby];
            for losing in tradeable.iter() {
                if recipe_amount == 0 {
                    let recipe_reduction = starting_qty - recipe_amount;
                    possible_strategies.push((recipe_reduction, Strategy::from(inv, actions.clone())))
                }
                inv = inv.trade(losing, &gaining, recipe_amount as i128);
                let gained = inv[&gaining];
                if gained != 0 {
                    let adjustment = min(recipe_amount, gained);
                    recipe_amount -= adjustment;
                    inv[&gaining] -= adjustment;
                    actions.push(Action::Trade)
                }
            }
            possible_strategies
        },
        Branch::Dismantle => {
            // potentially several strategies will result from this branch

            // find next non-zero inventory item and dismantle from it to
            // the current recipe item
            let mut dismantle_class: Class; let mut dismantle_name: Name;
            let mut to_try_dismantle: HashMap<Class, Name> = HashMap::new();
            for (item, _) in inv.non_zero() {
                Item(dismantle_class, dismantle_name, _) = item.clone();
                if dismantle_class == desired_class && Items::index_of(&desired_name) < Items::index_of(&dismantle_name) {
                    // if it's the same class, only try to dismantle from above
                    to_try_dismantle.entry(dismantle_class).or_insert(dismantle_name);
                } else if dismantle_class != desired_class {
                    // if it's from a different class, try to dismantle from anywhere
                    to_try_dismantle.entry(dismantle_class).or_insert(dismantle_name);
                }
            }
            for (class, name) in to_try_dismantle.into_iter() {
                if desired_class == class {
                    let recipe_item_idx = Items::index_of(&desired_name);
                    let mut idx = recipe_item_idx + 1;
                    let highest_idx = Items::last_of(&desired_class);
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
                            possible_strategies.push((recipe_reduction, Strategy::from(inv, vec![Action::Dismantle(cost)])));
                            return possible_strategies
                        }
                        idx += 1;
                    }
                } else {
                    // dismantle either until there will be enough for upgrades or we are out
                    // of items for the class
                }
                return possible_strategies
            }
            possible_strategies
        },
        Branch::Upgrade => possible_strategies,
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
pub fn find_strategy(recipe: Inventory, inventory: Inventory) -> Option<Strategy> {
    if inventory >= recipe {
        return Some(Strategy::new(inventory))
    }
    let mut strats: Vec<Strategy> = Vec::new();
    for (item, amount) in recipe.non_zero() {
        let Item(_, name, _) = item;
        for (i, branch) in [Branch::Trade, Branch::Upgrade, Branch::Dismantle].iter().enumerate() {
            let possible_strategies = exec_branch((item, amount), inventory.clone(), branch);
            if possible_strategies.len() != 0 {
                for (reduction, strategy) in possible_strategies.iter() {
                    let mut recipe = recipe.clone();
                    recipe[&name] -= reduction;
                    let further_strategy = find_strategy(recipe, strategy.inventory.clone());
                    if let Some(_further_strategy) = further_strategy {
                        strats.push(strategy.clone().merge(_further_strategy));
                    }
                }
            }
        }
    }
    if let Some(successful_strategy) = strats.iter().max() {
       return Some(successful_strategy.clone())
    }
    None
}

pub fn can_craft(recipe: Inventory, inventory: Inventory) -> bool {
    if let Some(_) = find_strategy(recipe, inventory) {
       return true
    }
    return false;
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
