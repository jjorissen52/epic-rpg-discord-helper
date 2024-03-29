use std::cmp::min;
use std::collections::{HashMap, HashSet};

use crate::crafting::{Action, Class, Inventory, Item, Items, Name, Strategy, TradeArea, TradeTable};
use crate::utils::{clamp};

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
        ruby,
        0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0
    ).log_value())
}

#[test]
fn test_future() {
    let res = future_logs(
        2,
        100_000, 0, 0, 0, 0, 0,
        0, 0, 0,
        0, 0,
        0,
    ).unwrap();
    let res = future_logs(
        10,
        0, 0, 0, 0, 0, 2,
        0, 0, 0,
        0, 0,
        0,
    ).unwrap();
    assert_eq!(res, 163840);
}

#[derive(Debug, PartialEq)]
pub enum Branch {
    Trade,
    Upgrade,
    Dismantle,
}

fn exec_branch(recipe: Inventory, mut inv: Inventory, target: &Name, branch: &Branch) -> Vec<Strategy> {
    let mut possible_strategies: Vec<Strategy> = Vec::new();
    let Item(desired_class, desired_name, _) = Items[target];
    match branch {
        // perform any free trades into the current recipe item's class
        Branch::Trade => {
            if !Items[target].is_craftable() { return possible_strategies }
            let mut actions: Vec<Action> = Vec::new();
            let gaining = Items[Items::first_of(&desired_class)].1;
            let tradeable = [&Name::WoodenLog, &Name::NormieFish, &Name::Apple, &Name::Ruby];
            for losing in tradeable.iter() {
                let before = inv[&gaining];
                inv = inv.trade(losing, &gaining, -1);
                let now = inv[&gaining];
                if now != before {
                    actions.push(Action::Trade)
                }
            }
            if actions.len() != 0 {
                possible_strategies.push(Strategy::from(inv, actions.clone()));
            }
        },
        // potentially several strategies will result from this branch
        Branch::Dismantle => {
            // find next non-zero inventory item and dismantle from it to
            // the current recipe item
            if !Items[target].is_craftable() { return possible_strategies }
            let mut dismantle_class: Class; let mut dismantle_name: Name;
            let mut to_try_dismantle: HashMap<Class, Name> = HashMap::new();
            // attempt dismantles for non-zero inventory items
            for (inv_item, _) in inv.non_zero() {
                if !inv_item.is_craftable() { continue };
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
                    working_inv[&name] = remainder;
                    working_inv[&desired_name] = qty;
                    possible_strategies.push(Strategy::from(working_inv, vec![Action::Dismantle(0)]));
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
                    possible_strategies.push(Strategy::from(working_inv, vec![Action::Dismantle(0)]));
                }
            }
        },
        // Starting with the item closest to the desired recipe item,
        // attempt to upgrade from it to the next tier
        Branch::Upgrade => {
            if !Items[target].is_craftable() { return possible_strategies }
            let mut should_craft = recipe.clone();
            let mut working_inv = inv.clone();
            let (start, end) = (Items::index_of(&target), Items::first_of(&desired_class));
            let mut idx = start;
            while idx > end {
                let desired_amount = should_craft[idx];
                let current_amount = working_inv[idx];
                let num_lower_tier_for_ug = Items[idx - 1].required_for_upgrade(&Items[idx].1);
                // if we already have enough of the higher tier, we craft none of the lower tier
                let num_lower_tier_needed = num_lower_tier_for_ug * (desired_amount - min(current_amount, desired_amount));
                // if we already have enough of the lower tier, we craft none, otherwise, we craft the difference
                should_craft[idx - 1] = num_lower_tier_needed - min(working_inv[idx - 1], num_lower_tier_needed);
                idx -= 1;
            }
            while idx < start {
                let (available, crafting, amount_to_craft) = (working_inv[idx], &Items[idx + 1].1, should_craft[idx + 1]);
                let (_, crafted, remainder) = Items[idx].upgrade_to(available, crafting, amount_to_craft);
                working_inv[idx] = remainder;
                working_inv[idx + 1] += crafted;
                idx += 1
            }
            if working_inv != inv {
                possible_strategies.push(Strategy::from(working_inv, vec![Action::Upgrade]))
            }
        },
    }
    possible_strategies
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
fn find_strategy(
    mut recipe: Inventory,
    mut inventory: Inventory,
    last_branch: Option<&Branch>,
    mut depth: usize,
) -> Option<(Inventory, Strategy)> {
    if depth > 10 {
        return None; // to save from combinatorial explosion
    }
    // remove from consideration items we already have
    for (item, amount) in recipe.non_zero() {
        let reduction = clamp(inventory[&item.1], 0, amount);
        recipe[&item.1] -=  reduction;
        inventory[&item.1] -= reduction;
    }
    if inventory >= recipe {
        //     (remaining recipe, crafting strategy)
        return Some((recipe, Strategy::new(inventory)))
    }
    let mut strats: Vec<(Inventory, Strategy)> = Vec::new();
    for (item, _) in recipe.non_zero() {
        let Item(_, name, _) = item;
        for branch in [Branch::Trade, Branch::Upgrade, Branch::Dismantle].iter() {
            if let Some(_last_branch) = last_branch {
                if _last_branch == branch { continue }
            }
            let possible_strategies = exec_branch(recipe, inventory, &name, branch);
            for strategy in possible_strategies.iter() {
                if let Some((recipe, further_strategy)) = find_strategy(recipe, strategy.inventory.clone(), Some(branch), depth + 1) {
                    strats.push((recipe, strategy.clone().merge(further_strategy)));
                };
            }
        }
    }

    if let Some((r, successful_strategy)) = strats.iter().filter(|(r, s)| s.inventory >= r.clone()).max() {
       return Some((r.clone(), successful_strategy.clone()))
    }
    None
}

fn _can_craft(recipe: Inventory, inventory: Inventory) -> bool {
    // Modifying the inventory ahead of time is not an issue
    // as long as we don't affect the "craftability"
    let mut inventory = inventory.clone();
    let mut first_relevant_class = Class::Log;
    for (item, _) in recipe.non_zero() {
        Item(first_relevant_class, ..) = item.into();
        break;
    }
    let relevant_classes: HashSet<Class> = recipe.non_zero().iter().map(|(item, qty)| &item.0).cloned().collect();
    for (item, _) in inventory.non_zero() {
        // if it's irrelevant, we just go ahead and fully dismantle it if craftable
        // or just remove it if not
        if !relevant_classes.contains(&item.0) {
            if item.is_craftable() {
                inventory = inventory.migrate(&item.0, &first_relevant_class, usize::MAX);
            } else {
                inventory[&item.1] = 0;
            }
        }
    }
    if let Some(_) = find_strategy(recipe, inventory, None, 0) {
       return true
    }
    return false;
}

pub fn can_craft(
    recipe: [u64; Items::INV_SIZE],
    inventory: [u64; Items::INV_SIZE],
    area: usize,
) -> bool {
    _can_craft(
        Inventory::from_array(TradeTable::from_usize(area).unwrap(), recipe),
        Inventory::from_array(TradeTable::from_usize(area).unwrap(), inventory)
    )
}

fn _how_many(
    recipe: Inventory,
    inventory: Inventory,
) -> usize {
    fn factor() -> usize { 5 };
    fn find_upper_bound(
        recipe: Inventory,
        inventory: Inventory,
        current: usize,
    ) -> usize {
        return if _can_craft(recipe, inventory) {
            find_upper_bound(recipe * factor(), inventory, current * factor())
        } else {
            current
        }
    }
    fn midpoint(a: usize, b: usize) -> usize { (b - a) / 2 + a }
    let mut b = find_upper_bound(recipe * factor(), inventory, factor());
    let mut a = if b > factor() { b / factor() } else { 0 };
    while b - a > 1 {
        let midpoint = midpoint(a, b);
        if _can_craft(recipe * midpoint, inventory) { a = midpoint } else { b = midpoint }
    }
    return if _can_craft(recipe * a, inventory) { a } else { b }
}

pub fn how_many(
    recipe: [u64; Items::INV_SIZE],
    inventory: [u64; Items::INV_SIZE],
    area: usize,
) -> (usize, [u64; Items::INV_SIZE]) {
    let recipe = Inventory::from_array(TradeTable::from_usize(area).unwrap(), recipe);
    let result = _how_many(
        recipe,
        Inventory::from_array(TradeTable::from_usize(area).unwrap(), inventory),
    );
    return (result, (recipe * result).inventory)
}

#[test]
fn test_find_strategy_terminates() {
    find_strategy(Inventory::new(TradeTable::A1), Inventory::new(TradeTable::A1), None, 0);

    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from_vec(TradeTable::A1, vec![(&Name::WoodenLog, 0)]);
    find_strategy(recipe, inv, None, 0);

    // ruby sword
    // equivalent to 2500 + 2500 + 400 logs
    let recipe = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Ruby, 5), (&Name::MegaLog, 1), (&Name::WoodenLog, 400)
    ]);
    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Apple, 171_000), (&Name::Banana, 37)
    ]);
    dbg!(find_strategy(recipe, inv, None, 0).unwrap());
}

#[test]
fn test_can_craft_with_trades() {

    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::NormieFish, 10)]);
    let inv = Inventory::from_vec(TradeTable::A1, vec![(&Name::WoodenLog, 10)]);
    assert!(_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A10, vec![(&Name::NormieFish, 10)]);
    let inv = Inventory::from_vec(TradeTable::A10, vec![(&Name::WoodenLog, 10)]);
    assert!(!_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A6, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from_vec(TradeTable::A6, vec![(&Name::Apple, 2)]);
    assert!(_can_craft(recipe.clone(), inv.clone()));

    // demonstrates a bug in the current implementation
    let recipe = Inventory::from_vec(TradeTable::A3, vec![(&Name::WoodenLog, 10)]);
    let inv = Inventory::from_vec(TradeTable::A3, vec![(&Name::Apple, 2)]);
    assert!(!_can_craft(recipe.clone(), inv.clone()));
}

#[test]
fn test_can_craft_with_dismantles() {
    let recipe = Inventory::from_vec(TradeTable::A6, vec![(&Name::NormieFish, 24)]);
    let inv = Inventory::from_vec(TradeTable::A6, vec![(&Name::EpicFish, 2)]);

    assert!(_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A6, vec![(&Name::WoodenLog, 163_840)]);
    let inv = Inventory::from_vec(TradeTable::A6, vec![(&Name::UltraLog, 2)]);
    assert!(_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A6, vec![(&Name::WoodenLog, 163_841)]);
    assert!(!_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A10, vec![(&Name::UltraLog, 1)]);
    let inv = Inventory::from_vec(TradeTable::A10, vec![(&Name::Banana, 1)]);
    assert!(!_can_craft(recipe.clone(), inv.clone()));
}

#[test]
fn test_can_craft_with_dismantles_and_trades() {
    // recipe equivalent of fish sword
    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::NormieFish, 20*12), (&Name::WoodenLog, 20*5)]);
    let inv = Inventory::from_vec(TradeTable::A1, vec![(&Name::EpicFish, 1)]);
    assert!(_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::NormieFish, 960)]);
    assert!(_can_craft(recipe.clone(), inv.clone()));

    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::NormieFish, 960), (&Name::WoodenLog, 1)]);
    assert!(!_can_craft(recipe.clone(), inv.clone()));

    // ruby sword
    let recipe = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Ruby, 5), (&Name::MegaLog, 1), (&Name::WoodenLog, 400)
    ]);
    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::MegaLog, 100000), (&Name::WoodenLog, 400)
    ]);
    assert!(_can_craft(recipe, inv));
}

#[test]
fn test_can_craft_with_upgrades() {
    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::MegaLog, 1)]);
    let inv = Inventory::from_vec(TradeTable::A1, vec![(&Name::WoodenLog, 2500)]);
    assert!(_can_craft(recipe, inv));

    let recipe = Inventory::from_vec(TradeTable::A1, vec![(&Name::GoldenFish, 10)]);
    let inv = Inventory::from_vec(TradeTable::A1, vec![(&Name::WoodenLog, 25)]);
    assert!(!_can_craft(recipe, inv));

    let recipe = Inventory::from_vec(
        TradeTable::A10, vec![(&Name::WoodenLog, 1000), (&Name::UltraLog, 1)]
    );
    let inv = Inventory::from_vec(
        TradeTable::A10, vec![(&Name::Apple, 170_000)]
    );
    assert!(_can_craft(recipe, inv));
}

#[test]
fn test_can_craft_only() {
    // ruby sword
    // equivalent to 2500 + 2500 + 400 logs
    let recipe = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Ruby, 5), (&Name::MegaLog, 1), (&Name::WoodenLog, 400)
    ]);
    let inv = recipe.clone();
    assert!(_can_craft(recipe, inv));

    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Ruby, 10), (&Name::WoodenLog, 400)
    ]);
    assert!(_can_craft(recipe, inv));

    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::SuperLog, 100000), (&Name::WoodenLog, 400)
    ]);
    assert!(_can_craft(recipe, inv));

    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::MermaidHair, 1), (&Name::WoodenLog, 400)
    ]);
    assert!(!_can_craft(recipe, inv));

    // takes way too long
    let inv = Inventory::from_vec(TradeTable::A10, vec![
        (&Name::Apple, 171_000), (&Name::Banana, 1000)
    ]);
    // assert!(_can_craft(recipe, inv));
    dbg!(find_strategy(recipe, inv, None, 0).unwrap().1.inventory.log_value());
}

#[test]
fn test_how_many() {
    // apple=25, banana=6
    let recipe = Inventory::from_vec(
        TradeTable::A10, vec![(&Name::Apple, 25), (&Name::Banana, 6)]
    );
    let inv = Inventory::from_vec(TradeTable::A10, vec![(&Name::Apple, 100_000)]);
    assert_eq!(_how_many(recipe, inv), 869)
}
