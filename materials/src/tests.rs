use crate::crafting::{Name, TradeTable, Inventory, Item, Items, Class, Strategy, Action};

#[test]
fn test_logs_required_for_upgrade() {
    assert_eq!(3*15*100*10, Items[&Name::EpicFish].logs_required_for_upgrade(10, TradeTable::A10));
    assert_eq!(12*15*100, Items[&Name::Banana].logs_required_for_upgrade(100, TradeTable::A10));
}

#[test]
fn test_adjustment() {
    let mut inv = Inventory::new(TradeTable::A1);
    inv[&Name::Apple] += 89000;
    inv[&Name::Apple] += 125;
    inv[&Name::Apple] -= 125;
    assert_eq!(89000, inv[&Name::Apple]);
}

#[test]
fn test_trade() {
    let apples = 89000;
    let mut inv = Inventory::from(TradeTable::A3, vec![(&Name::Apple, apples)]);
    inv = inv.trade(&Name::Apple, &Name::WoodenLog, -1);
    assert_eq!(inv[&Name::WoodenLog], apples*3);
    inv = inv.trade(&Name::WoodenLog, &Name::Apple, -1);
    assert_eq!(inv[&Name::Apple], apples);
}

#[test]
fn test_dismantle() {
    let (maybe_hyper_log, qty) = Items[&Name::UltraLog].dismantle(1);
    let hyper_log = Items[&Name::HyperLog];

    assert_eq!(maybe_hyper_log, hyper_log);
    assert_eq!(qty, 8);

    let (maybe_wooden_log, qty) = hyper_log.full_dismantle(8);
    assert_eq!(maybe_wooden_log, Items[&Name::WoodenLog]);
    assert_eq!(81920, qty);

    let (maybe_golden_fish, qty) = Items[&Name::EpicFish].dismantle(2);
    assert_eq!(maybe_golden_fish, Items[&Name::GoldenFish]);
    assert_eq!(80*2, qty);
}

#[test]
fn test_dismantle_to() {
    let ultra_log = Items[&Name::UltraLog];
    let (desired_amount, name) = (150_000, &Name::WoodenLog);
    let (qty, remainder) = ultra_log.dismantle_to(3, name, desired_amount);
    assert_eq!((qty, remainder), (163_840, 1));

    let epic_fish = Items[&Name::EpicFish];
    let (desired_amount, name) = (3000, &Name::GoldenFish);
    let (qty, remainder) = epic_fish.dismantle_to(1_000, name, desired_amount);
    assert_eq!((qty, remainder), (3040, 962))
}

#[test]
fn test_dismantle_cost() {
    let ultra_log = Items[&Name::UltraLog];
    let (desired_amount, name) = (150_000, &Name::WoodenLog);
    let (qty, remainder) = ultra_log.dismantle_to(3, name, desired_amount);
    // amount lost from original material cost
    let cost: u64 = 250_000 * 2 - 163_840;
    assert_eq!(cost, Item::dismantle_cost(0, 5, 163_840))
}

#[test]
fn test_migrate() {
    let mut inv = Inventory::from(
        TradeTable::A2, vec![(&Name::EpicFish, 10), (&Name::GoldenFish, 0), (&Name::NormieFish, 0)]
    );
    let inv = inv.migrate(&Class::Fish, &Class::Log, 5);
    assert_eq!(inv[&Name::WoodenLog], 9600);
}

#[test]
fn test_migrate_all() {
    let mut inv = Inventory::new(TradeTable::A8);
    let counts: [(&Name, u64, u64); 8] = [
        (&Name::EpicFish, 100, 0),
        (&Name::GoldenFish, 15, 0),
        (&Name::NormieFish, 1, 0),
        (&Name::Banana, 100, 0),
        (&Name::Apple, 1000, 0),
        (&Name::Ruby, 10, 0),
        (&Name::HyperLog, 5, 5),
        (&Name::WoodenLog, 10, 312903),
    ];
    for &(name, initial, _) in counts.iter() {
        inv[name] += initial
    }
    let inv = inv.migrate_all(&Class::Log, 100);

    for &(name, _, fin) in counts.iter() {
        assert_eq!(inv[name], fin);
    }
}


#[test]
fn test_upgrade() {
    let (maybe_epic_log, result, remainder) = Items[&Name::WoodenLog].upgrade(53);
    let epic_log = Items[&Name::EpicLog];
    assert_eq!(maybe_epic_log, epic_log);
    assert_eq!(result, 2);
    assert_eq!(remainder, 3);

    let (maybe_ultra_log, result, remainder) = Items[&Name::WoodenLog].upgrade_to(750_011, &Name::UltraLog, 2);
    let ultra_log = Items[&Name::UltraLog];
    assert_eq!(maybe_ultra_log, ultra_log);
    assert_eq!(result, 2);
    assert_eq!(remainder, 250_011);

    let (maybe_epic_fish, result, remainder) = Items[&Name::NormieFish].upgrade_to(2001, &Name::EpicFish, 2);
    let epic_fish = Items[&Name::EpicFish];
    assert_eq!(maybe_epic_fish, epic_fish);
    assert_eq!(result, 1);
    assert_eq!(remainder, 501)
}

#[test]
fn test_strategy(){
    let inv = Inventory::from(TradeTable::A3, vec![(&Name::WoodenLog, 10)]);
    let ug = Strategy::from(inv.clone(), vec![Action::Upgrade]);
    let dg = Strategy::from(inv.clone(), vec![Action::Dismantle(100)]);
    // end inventory is the same and same number of steps, so strategies are equivalent
    assert_eq!(dg, ug);

    let mut inv = Inventory::from(TradeTable::A3, vec![(&Name::WoodenLog, 10)]);
    let s1 = Strategy::from(inv.clone(), vec![Action::Upgrade]);
    inv[&Name::WoodenLog] -= 1;
    let s2 = Strategy::from(inv.clone(), vec![Action::Dismantle(100)]);
    // inventory in strategy 2 is strictly worse
    assert!(s1 > s2);
    assert!(s2 < s1);
    assert_ne!(s1, s2);

    let s2 = Strategy::from(inv.clone(), vec![]);
    // inventory in strategy 2 is still strictly worse
    assert!(s1 > s2);
    assert!(s2 < s1);
    assert_ne!(s1, s2);
}

#[test]
fn it_works() {
    let apples = 89000;
    let mut inv = Inventory::from(TradeTable::A7, vec![(&Name::Apple, apples)]);
    inv = inv.trade(&Name::Apple, &Name::WoodenLog, -1).next_area().unwrap(); // trade in A7
    inv = inv.trade(&Name::WoodenLog, &Name::Apple, -1).next_area().unwrap(); // A8
    inv = inv.trade(&Name::Apple, &Name::NormieFish, -1).next_area().unwrap(); // A9
    inv = inv.trade(&Name::NormieFish, &Name::WoodenLog, -1); // A10
    assert_eq!(inv.get_area(), TradeTable::A10);
}
