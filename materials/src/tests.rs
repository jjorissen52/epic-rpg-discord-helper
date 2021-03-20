use crate::crafting::{Name, TradeTable, Inventory, Items, Class, Strategy, Action};

#[test]
fn test_adjustment() {
    let mut inv = Inventory::new();
    inv = inv.adjustment(&Name::Apple, 89000);
    let copy = inv.clone();
    inv = inv.adjustment(&Name::Apple, 125);
    assert!(inv > copy);
    inv = inv.adjustment(&Name::Apple, -125);
    assert_eq!(inv, copy)
}

#[test]
fn test_trade() {
    let apples = 89000;
    let mut inv = Inventory::new();
    inv = inv.adjustment(&Name::Apple, apples);
    inv = inv.trade(&Name::Apple, &Name::WoodenLog, -1, TradeTable::A3);
    let (_, qty) = inv.get_item(&Name::WoodenLog);
    assert_eq!(qty, (apples*3) as u64);
    inv = inv.trade(&Name::WoodenLog, &Name::Apple, -1, TradeTable::A3);
    let (_, qty) = inv.get_item(&Name::Apple);
    assert_eq!(qty, apples as u64);
}

#[test]
fn test_dismantle() {
    let (maybe_hyper_log, qty) = Items::get_item(&Name::UltraLog).dismantle(1);
    let hyper_log = Items::get_item(&Name::HyperLog);

    assert_eq!(maybe_hyper_log, hyper_log);
    assert_eq!(qty, 8);

    let (maybe_wooden_log, qty) = hyper_log.full_dismantle(8);
    let wooden_log = Items::get_item(&Name::WoodenLog);
    assert_eq!(maybe_wooden_log, wooden_log);
    assert_eq!(81920, qty);

    let (maybe_golden_fish, qty) = Items::get_item(&Name::EpicFish).dismantle(2);
    let golden_fish = Items::get_item(&Name::GoldenFish);
    assert_eq!(golden_fish, maybe_golden_fish);
    assert_eq!(80*2, qty);
}

#[test]
fn test_dismantle_to() {
    let ultra_log = Items::get_item(&Name::UltraLog);
    let (desired_amount, name) = (150_000, &Name::WoodenLog);
    let (qty, remainder) = ultra_log.dismantle_to(3, name, desired_amount);
    assert_eq!((qty, remainder), (163_840, 1));

    let epic_fish = Items::get_item(&Name::EpicFish);
    let (desired_amount, name) = (3000, &Name::GoldenFish);
    let (qty, remainder) = epic_fish.dismantle_to(1_000, name, desired_amount);
    assert_eq!((qty, remainder), (3040, 962))
}

#[test]
fn test_migrate() {
    let mut inv = Inventory::new();
    inv = inv.adjustment(&Name::EpicFish, 10);
    inv = inv.adjustment(&Name::GoldenFish, 0);
    inv = inv.adjustment(&Name::NormieFish, 0);
    let (inv, _) = inv.migrate(&Class::Fish, &Class::Log, 5, TradeTable::A2);
    assert_eq!(inv.get_item(&Name::WoodenLog).1, 9600);
}

#[test]
fn test_migrate_all() {
    let mut inv = Inventory::new();
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
        inv = inv.adjustment(name, initial as i128)
    }
    let (inv, _) = inv.migrate_all(&Class::Log, 100, TradeTable::A8);

    for &(name, _, fin) in counts.iter() {
        assert_eq!(inv.get_qty(name), fin);
    }
}


#[test]
fn test_upgrade() {
    let (maybe_epic_log, result, remainder) = Items::get_item(&Name::WoodenLog).upgrade(53);
    let epic_log = Items::get_item(&Name::EpicLog);
    assert_eq!(maybe_epic_log, epic_log);
    assert_eq!(result, 2);
    assert_eq!(remainder, 3);

    let (maybe_ultra_log, result, remainder) = Items::get_item(&Name::WoodenLog).upgrade_to(750_011, &Name::UltraLog, 2);
    let ultra_log = Items::get_item(&Name::UltraLog);
    assert_eq!(maybe_ultra_log, ultra_log);
    assert_eq!(result, 2);
    assert_eq!(remainder, 250_011);

    let (maybe_epic_fish, result, remainder) = Items::get_item(&Name::NormieFish).upgrade_to(2001, &Name::EpicFish, 2);
    let epic_fish = Items::get_item(&Name::EpicFish);
    assert_eq!(maybe_epic_fish, epic_fish);
    assert_eq!(result, 1);
    assert_eq!(remainder, 501)
}

#[test]
fn test_strategy(){
    let ug = Strategy::from(vec![Action::Upgrade]);
    let dg = Strategy::from(vec![Action::Dismantle(100)]);
    assert!(dg > ug);
    assert!(ug < dg);
}

#[test]
fn it_works() {
    let mut inv = Inventory::new();
    let apples = 89000;
    inv = inv.adjustment(&Name::Apple, apples);
    inv = inv.trade(&Name::Apple, &Name::WoodenLog, -1, TradeTable::A7);
    inv = inv.trade(&Name::WoodenLog, &Name::Apple, -1, TradeTable::A8);
    inv = inv.trade(&Name::Apple, &Name::NormieFish, -1, TradeTable::A9);
    inv = inv.trade(&Name::NormieFish, &Name::WoodenLog, -1, TradeTable::A10);
    dbg!(inv);
}
