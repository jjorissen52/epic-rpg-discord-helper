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

fn exec_branch(mut recipe: Inventory, mut inv: Inventory, target: &Name, branch: &Branch) -> Vec<(Inventory, Strategy)> {
    let mut possible_strategies: Vec<(Inventory, Strategy)> = Vec::new();
    let Item(desired_class, desired_name, _) = Items[target];
    match branch {
        Branch::Trade => {
            // perform any free trades into the current recipe item's class
            let mut actions: Vec<Action> = Vec::new();
            let gaining = Items[Items::first_of(&desired_class)].1;
            let tradeable = [&Name::WoodenLog, &Name::NormieFish, &Name::Apple, &Name::Ruby];
            for losing in tradeable.iter() {
                let before = inv[&gaining];
                inv = inv.trade(losing, &gaining, -1);
                let now = inv[&gaining];
                if now != before {
                    let adjustment = min(recipe[&gaining], now);
                    recipe[&gaining] -= adjustment;
                    inv[&gaining] -= adjustment;
                    actions.push(Action::Trade)
                }
            }
            if actions.len() != 0 {
                possible_strategies.push((recipe, Strategy::from(inv, actions.clone())));
            }
            possible_strategies
        },
        Branch::Dismantle => {
            // potentially several strategies will result from this branch

            // find next non-zero inventory item and dismantle from it to
            // the current recipe item
            let mut dismantle_class: Class; let mut dismantle_name: Name;
            let mut to_try_dismantle: HashMap<Class, Name> = HashMap::new();
            // attempt dismantles for non-zero inventory items
            for (inv_item, _) in inv.non_zero() {
                Item(dismantle_class, dismantle_name, _) = inv_item.clone();
                if dismantle_class == desired_class && Items::index_of(&desired_name) < Items::index_of(&dismantle_name) {
                    // If it's the same class, try to dismantle from above.
                    // The hashmap entry will always be the first non-zero inventory item
                    // of a tier higher than the current recipe item
                    to_try_dismantle.entry(dismantle_class).or_insert(dismantle_name);
                } else if dismantle_class != desired_class && Items::first_of(&dismantle_class) < Items::index_of(&dismantle_name)  {
                    // If it's from a different class, we can try to dismantle as long as it isn't already
                    // the base tier of its class.
                    to_try_dismantle.entry(dismantle_class).or_insert(dismantle_name);
                }
            }
            for (class, name) in to_try_dismantle.into_iter() {
                let mut working_inv = inv.clone();
                if desired_class == class {
                    let available = working_inv[&name];
                    let (qty, remainder) = Items[&name].dismantle_to(available, &desired_name, recipe[target]);
                    let recipe_reduction = min(qty, recipe[target]);
                    working_inv[&desired_name] = qty - recipe_reduction;
                    working_inv[&name] = remainder;
                    recipe[target] -= recipe_reduction;
                    possible_strategies.push((recipe, Strategy::from(working_inv, vec![Action::Dismantle(0)])));
                } else {
                    // dismantle either until there will be enough for upgrades or we are out
                    // of items for the class
                    let logs_required = Items[Items::index_of(target)].logs_required_for_upgrade(recipe[target], inv.get_area());
                    let exchange_rate = if &class == &Class::Log { 1 } else {
                        TradeTable::rate_from_logs(inv.get_area(), &class).denominator
                    };
                    // how many of the base tier of this class we will need
                    let base_required = logs_required / exchange_rate + logs_required % exchange_rate;
                    let base_tier_index = Items::first_of(&class);
                    let base_name = Items[base_tier_index].1;
                    let (result, remainder) = Items[&name].dismantle_to(working_inv[&name], &base_name, base_required);
                    working_inv[&name] = remainder;
                    working_inv[base_tier_index] = result;
                    possible_strategies.push((recipe, Strategy::from(working_inv, vec![Action::Dismantle(0)])));
                }
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
