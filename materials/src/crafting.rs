#![allow(dead_code)]

use std::cmp::{min, Ordering};
use std::ops::Index;

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum Class {
    Log = 0,
    Fish,
    Fruit,
    Gem,
    Lootbox,
    Cookie,
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum Name {
    WoodenLog = 0,
    EpicLog,
    SuperLog,
    MegaLog,
    HyperLog,
    UltraLog,
    NormieFish,
    GoldenFish,
    EpicFish,
    Apple,
    Banana,
    Ruby,
    CommonLootbox,
    UncommonLootbox,
    RareLootbox,
    EpicLootbox,
    EdgyLootbox,
    OmegaLootbox,
    GodlyLootbox,
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum Action {
    Upgrade,
    Dismantle(u64),
    Trade,
    Terminate(bool), // success or failure
}
#[derive(Debug, Eq)]
pub struct Strategy(Vec<Action>);

impl Strategy {
    pub fn new() -> Strategy {
        let mut vec = Vec::new();
        Strategy(vec)
    }

    pub fn from(vec: Vec<Action>) -> Strategy {
        Strategy(vec)
    }

    pub fn into_vec(self) -> Vec<Action> {
        self.0
    }

    pub fn add(self, action: Action) -> Strategy {
        let Strategy(mut vec) = self;
        vec.push(action);
        Strategy(vec)
    }

    pub fn concat(self, other: Strategy) -> Strategy {
        let Strategy(_other) = other;
        self.extend(_other)
    }

    pub fn extend(self, vec: Vec<Action>) -> Strategy {
        let Strategy(mut _vec) = self;
        _vec.extend(vec);
        Strategy(_vec)
    }

    pub fn terminal(&self) -> bool {
        let Strategy(inner) = self;
        if inner.len() == 0 {
            return false
        }
        match inner[inner.len() -1] {
            Action::Terminate(_) => true,
            _ => false
        }
    }

    fn cost(&self) -> u64 {
        let Strategy(strat) = self;
        let mut self_cost = 0;
        for action in strat.iter() {
            match action {
                Action::Dismantle(cost) => { self_cost += cost },
                Action::Terminate(success) => return if *success { 0 } else { u64::MAX },
                _ => {},
            }
        }
        return self_cost
    }
}

impl Clone for Strategy {

    fn clone(&self) -> Strategy {
        let Strategy(actions) = self;
        Strategy(actions.clone())
    }
}

impl Ord for Strategy {
    fn cmp(&self, other: &Self) -> Ordering {
        let (c1, c2) = (self.cost(), other.cost());
        let (Strategy(s1), Strategy(s2)) = (self, other);
        return if c1 == c2 {
            s1.len().cmp(&s2.len())
        } else {
            c1.cmp(&c2)
        }
    }
}

impl PartialOrd for Strategy {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(&other))
    }
}

impl PartialEq for Strategy {
    fn eq(&self, other: &Self) -> bool {
        let (c1, c2) = (self.cost(), other.cost());
        let (Strategy(s1), Strategy(s2)) = (self, other);
        c1 == c2 && s1.len() == s2.len()
    }
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub struct Item(pub Class, pub Name, pub u32);
impl Item {
    pub fn is_tradeable(&self) -> bool {
        let Item(class, _, _) = &self;
        match class {
            Class::Log => true,
            Class::Fish => true,
            Class::Fruit => true,
            Class::Gem => true,
            _ => false,
        }
    }

    pub fn dismantle(&self, qty: u64) -> (Item, u64) {
        let Item(_, name, value) = &self;
        let idx = Items::index_of(&name);
        if *value == 1 {
            return (self.clone(), qty)
        }
        (Items[idx - 1], qty * (value * 4 / 5) as u64)
    }

    pub fn dismantle_to(&self, mut available: u64, to: &Name, mut amount: u64) -> (Item, u64, u64) {
        let mut current_qty: u64 = 0;
        let mut current_item = self.clone();
        let Item(_, losing_name, _) = current_item;
        let start_idx = Items::index_of(&losing_name);
        let end_idx = Items::index_of(to);
        while available != 0 && current_qty < amount  {
            let mut qty: u64 = 1;
            let mut idx = start_idx;
            current_item = self.clone();
            while idx > end_idx {
                (current_item, qty) = current_item.dismantle(qty);
                idx -= 1;
            }
            current_qty += qty;
            available -= 1;
        }
        // (Item, qty, remainder)
        (current_item, current_qty, available)
    }

    pub fn full_dismantle(&self, mut qty: u64) -> (Item, u64) {
        let (mut item, mut dqty) = self.dismantle(qty);
        while dqty > qty {
            qty = dqty;
            (item, dqty) = item.dismantle(dqty);
        }
        (item, dqty)
    }

    pub fn upgrade(&self, available: u64) -> (Item, u64, u64) {
        let Item(class, name, _) = &self;
        let idx = Items::index_of(&name);
        if idx == Items::last_of(class) { return (self.clone(), 0, available); }

        let Item(_, _, cost) = Items[idx + 1];
        let remainder = available % cost as u64;
        (Items[idx + 1], available / cost as u64, remainder)
    }

    pub fn upgrade_to(&self, available: u64, to: &Name, mut amount: u64) -> (Item, u64, u64) {
        let Item(_, name, _) = self;

        let end = Items::index_of(to);
        let start = Items::index_of(name);

        let mut cost: u64 = 1;
        for i in (start..end + 1).rev() {
            let Item(_, _, value) = Items[i];
            cost *= value as u64;
        }

        if amount * cost > available {
            amount = available / cost;
        }
        let total_cost = amount * cost;
        let (mut item, mut cost, mut remainder) = (self.clone(), total_cost, 0 as  u64);
        for i in start..end {
            (item, cost, remainder) = Items[i].upgrade(cost);
            assert_eq!(remainder, 0);
        }
        (item, amount, available - total_cost)
    }
}

pub struct Items;
impl Items {
    pub const INV_SIZE: usize = 19;

    const ITEMS: [Item; Items::INV_SIZE] = [
        Item(Class::Log, Name::WoodenLog, 1),
        Item(Class::Log, Name::EpicLog, 25),
        Item(Class::Log, Name::SuperLog, 10),
        Item(Class::Log, Name::MegaLog, 10),
        Item(Class::Log, Name::HyperLog, 10),
        Item(Class::Log, Name::UltraLog, 10),
        Item(Class::Fish, Name::NormieFish, 1),
        Item(Class::Fish, Name::GoldenFish, 15),
        Item(Class::Fish, Name::EpicFish, 100),
        Item(Class::Fruit, Name::Apple, 1),
        Item(Class::Fruit, Name::Banana, 15),
        Item(Class::Gem, Name::Ruby, 1),
        Item(Class::Lootbox, Name::CommonLootbox, 1),
        Item(Class::Lootbox, Name::UncommonLootbox, 1),
        Item(Class::Lootbox, Name::RareLootbox, 1),
        Item(Class::Lootbox, Name::EpicLootbox, 1),
        Item(Class::Lootbox, Name::EdgyLootbox, 1),
        Item(Class::Lootbox, Name::OmegaLootbox, 1),
        Item(Class::Lootbox, Name::GodlyLootbox, 1),
    ];

    pub fn index_of(name: &Name) -> usize {
        for i in 0..Items::INV_SIZE {
            let Item(_, _name, _) = Items[i];
            if _name == *name {
                return i
            }
        }
        return usize::max_value() // not possible
    }

    pub fn get_item(name: &Name) -> Item {
        return Items[Items::index_of(name)]
    }

    pub fn first_of(class: &Class) -> usize {
        for i in 0..Items::INV_SIZE {
            let Item(_class, _, _) = Items[i];
            if _class == *class {
                return i
            }
        }
        return usize::MAX // not possible
    }

    pub fn last_of(class: &Class) -> usize {
        let mut flag = false;
        for i in 0..Items::INV_SIZE {
            let Item(_class, _, _) = &Items[i];
            if class == _class {
                flag = true // flag indicates that we are in the correct class
            } else if flag {
                // we have gone past the correct class, so we want the last one
                return i - 1
            }
        }
        return Items::INV_SIZE
    }
}

impl Index<usize> for Items {
    type Output = Item;
    fn index(&self, index: usize) -> &Self::Output {
        &Items::ITEMS[index]
    }
}

#[non_exhaustive]
pub struct TradeTable;

pub type TradeArea = (usize, usize, usize, u8);

impl TradeTable {
    //          ratio of (fish, apple, ruby):log
    pub const A1: TradeArea = (1, 0, 0, 1);
    pub const A2: TradeArea = (1, 0, 0, 2);
    pub const A3: TradeArea = (1, 3, 0, 3);
    pub const A4: TradeArea = (2, 4, 0, 4);
    pub const A5: TradeArea = (2, 4, 450, 5);
    pub const A6: TradeArea = (3, 15, 675, 6);
    pub const A7: TradeArea = (3, 15, 675, 7);
    pub const A8: TradeArea = (3, 8, 675, 8);
    pub const A9: TradeArea = (2, 12, 850, 9);
    pub const A10: TradeArea = (3, 12, 500, 10);
    pub const A11: TradeArea = (3, 8, 500, 11);
    pub const A12: TradeArea = (3, 8, 350, 12);
    pub const A13: TradeArea = (3, 8, 350, 13);
    pub const A14: TradeArea = (3, 8, 350, 14);

    pub fn from_usize(area: usize) -> Option<TradeArea> {
        match area {
            1 => Some(TradeTable::A1),
            2 => Some(TradeTable::A2),
            3 => Some(TradeTable::A3),
            4 => Some(TradeTable::A4),
            5 => Some(TradeTable::A5),
            6 => Some(TradeTable::A6),
            7 => Some(TradeTable::A7),
            8 => Some(TradeTable::A8),
            9 => Some(TradeTable::A9),
            10 => Some(TradeTable::A10),
            11 => Some(TradeTable::A11),
            12 => Some(TradeTable::A12),
            13 => Some(TradeTable::A13),
            14 => Some(TradeTable::A14),
            _ => None
        }
    }

    pub fn next_area(area: TradeArea) -> Option<TradeArea> {
        match area {
            TradeTable::A1 => Some(TradeTable::A2),
            TradeTable::A2 => Some(TradeTable::A3),
            TradeTable::A3 => Some(TradeTable::A4),
            TradeTable::A4 => Some(TradeTable::A5),
            TradeTable::A5 => Some(TradeTable::A6),
            TradeTable::A6 => Some(TradeTable::A7),
            TradeTable::A7 => Some(TradeTable::A8),
            TradeTable::A8 => Some(TradeTable::A9),
            TradeTable::A9 => Some(TradeTable::A10),
            TradeTable::A10 => Some(TradeTable::A11),
            TradeTable::A11 => Some(TradeTable::A12),
            TradeTable::A12 => Some(TradeTable::A13),
            TradeTable::A13 => Some(TradeTable::A14),
            _ => None,
        }
    }
}

#[derive(Debug, Copy, Clone, Eq)]
pub struct Inventory([u64; Items::INV_SIZE]);

impl Inventory {
    pub fn new() -> Inventory {
        Inventory([0; Items::INV_SIZE])
    }

    pub fn from(vec: Vec<(&Name, u64)>) -> Inventory {
        let mut inv = Inventory::new();
        for item in vec.iter() {
            inv = inv.adjustment(item.0, item.1 as i128)
        }
        inv
    }

    pub fn itemized(
        wooden_log: u64, epic_log: u64, super_log: u64, mega_log: u64, hyper_log: u64, ultra_log: u64,
        normie_fish: u64, golden_fish: u64, epic_fish: u64,
        apple: u64, banana: u64,
        ruby: u64,
    ) -> Inventory {
        Inventory([
            wooden_log, epic_log, super_log, mega_log, hyper_log, ultra_log,
            normie_fish, golden_fish, epic_fish,
            apple, banana,
            ruby,
            0, 0, 0, 0, 0, 0, 0
        ])
    }

    pub fn len(&self) -> usize {
        let mut length = 0;
        for _ in self.non_zero() {
            length += 1
        }
        length
    }

    pub fn non_zero(&self) -> Vec<(Item, u64)> {
        let mut vec = Vec::new();
        let Inventory(inner) = self;
        for i in 0..Items::INV_SIZE {
            if inner[i] != 0 {
                vec.push((Items[i], inner[i]))
            }
        }
        vec
    }

    pub fn adjustment(&self, name: &Name, amount: i128) -> Inventory {
        let Inventory(mut inner) = self;
        for i in 0..Items::INV_SIZE {
            let Item(_, _name, _) = &Items[i];
            if _name == name {
                inner[i] = (inner[i] as i128 + amount) as u64;
                return Inventory(inner)
            }
        }
        panic!("No such item!")
    }

    pub fn get_item(&self, name: &Name) -> (Item, u64) {
        let i = Items::index_of(name);
        let Inventory(inner) = &self;
        (Items[i], inner[i])
    }

    pub fn get_qty(&self, name: &Name) -> u64 {
        let i = Items::index_of(name);
        let Inventory(inner) = &self;
        inner[i]
    }

    pub fn trade(self, losing: &Name, gaining: &Name, qty: i128, area: TradeArea) -> Inventory {
        let target_qty = if qty < 0 { i128::MAX } else { qty };
        let (litem, mut lqty) = &self.get_item(losing);
        let (gitem, _) = &self.get_item(gaining);
        if litem.is_tradeable() && gitem.is_tradeable() {
            let (fish, apple, ruby, _) = area;
            let (Item(litem_cls, _, _), Item(gitem_cls, _, _)) = (litem, gitem);
            if litem_cls == gitem_cls {
                return self;
            } else if litem_cls != &Class::Log && gitem_cls != &Class::Log {
                return self.trade(losing, &Name::WoodenLog, -1, area)
                    .trade(&Name::WoodenLog, gaining, target_qty, area)
            }
            return match (litem_cls, gitem_cls) {
                (Class::Log, _) => {
                    let mut gqty: i128 = 0;
                    let mut total_cost: i128 = 0;
                    let exchange_rate = match gitem_cls {
                        Class::Fish => fish,
                        Class::Fruit => apple,
                        Class::Gem => ruby,
                        _ => panic!("not possible."),
                    };
                    while lqty / exchange_rate as u64 > 0 && gqty < target_qty {
                        gqty += 1;
                        lqty -= exchange_rate as u64;
                        total_cost += exchange_rate as i128;
                    };
                    self.adjustment(losing, -total_cost).adjustment(gaining, gqty)
                },
                (_, Class::Log) => {
                    let exchange_rate = match litem_cls {
                        Class::Fish => fish,
                        Class::Fruit => apple,
                        Class::Gem => ruby,
                        _ => panic!("not possible."),
                    };
                    let exchange_qty = if target_qty < lqty as i128 { target_qty } else { lqty as i128 };
                    self.adjustment(losing, -exchange_qty)
                        .adjustment(gaining, exchange_qty * exchange_rate as i128)
                },
                _ => { panic!("Other cases handled by if block.") }
            }
        }
        panic!("Cannot be done!!!!");
    }

    pub fn migrate(&self, start: &Class, end: &Class, mut max_dismantle: usize, area: TradeArea) -> (Inventory, Strategy) {
        let mut strategy = Strategy::new();
        if start == end {
            return (self.clone(), strategy) // nothing to do
        }
        let base_idx = Items::first_of(start);
        max_dismantle = min(max_dismantle, Items::last_of(start) - base_idx);
        let &Inventory(mut inner) = &self;

        let mut idx = base_idx + max_dismantle;
        while idx > base_idx {
            strategy = strategy.add(Action::Dismantle(inner[idx]));
            let (_, qty) = Items[idx].dismantle(inner[idx]);
            inner[idx] = 0;
            idx -= 1;
            inner[idx] += qty;
        }
        let result_idx = Items::first_of(end);
        strategy = strategy.add(Action::Trade);
        return (Inventory(inner).trade(&Items[base_idx].1, &Items[result_idx].1, -1, area), strategy);
    }

    pub fn migrate_all(&self, to_class: &Class, max_steps: usize, area: TradeArea) -> (Inventory, Strategy) {
        let (inv, s1) = self.clone().migrate(&Class::Gem, to_class, max_steps, area);
        let (inv, s2) = inv.migrate(&Class::Fish, to_class, max_steps, area);
        let (inv, s3) = inv.migrate(&Class::Fruit, to_class, max_steps, area);
        let (inv, s4) = inv.migrate(&Class::Log, to_class, max_steps, area);
        return (inv, s1.concat(s2).concat(s3).concat(s4))
    }

    pub fn future(&self, start: TradeArea, end: TradeArea) -> Inventory {
        fn discard_strategy(fut: (Inventory, Strategy)) -> Inventory {
            let (inv, _) = fut;
            inv
        }
        let all = 10; // used as an indicator to dismantle all
        let (new_inv, _) = match start {
            TradeTable::A3 => self.migrate_all(&Class::Fish, all, start),
            TradeTable::A5 => self.migrate_all(&Class::Fruit, all, start),
            TradeTable::A7 => self.migrate(&Class::Fruit, &Class::Log, all, start),
            TradeTable::A8 => {
                // dismantle tier 4 logs and fish (mega log and epic fish), get fruit
                let tier = 4;
                discard_strategy(self.migrate(&Class::Log, &Class::Fruit, tier, start))
                    .migrate(&Class::Fish, &Class::Fruit, tier, start)
            },
            TradeTable::A9 => {
                // dismantle tier 2 logs and fruit (epic log and banana), get fish
                let tier = 2;
                discard_strategy(self.migrate(&Class::Log, &Class::Fish, tier, start))
                    .migrate(&Class::Fruit, &Class::Fish, tier, start)
            },
            TradeTable::A10 => {
                self.migrate(&Class::Fruit, &Class::Log, all, start)
            },
            // Make sure nothing is in rubies and have things in logs as the universal currency
            TradeTable::A11 => self.migrate_all(&Class::Log, all, start),
            _ => (self.clone(), Strategy::new())
        };
        if let Some(next_area) = TradeTable::next_area(start) {
            return new_inv.future(next_area, end)
        }
        new_inv
    }
}


impl Ord for Inventory {
    fn cmp(&self, other: &Self) -> Ordering {
        self.cmp(other)
    }
}

impl PartialOrd for Inventory {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }

    fn lt(&self, other: &Self) -> bool {
        !self.ge(other)
    }

    fn le(&self, other: &Self) -> bool {
        let self_items = self.0;
        let other_items = other.0;
        self_items.iter().enumerate().all(|(i, qty)| qty <= &other_items[i])
    }

    fn gt(&self, other: &Self) -> bool {
        !self.le(other)
    }

    fn ge(&self, other: &Self) -> bool {
        let self_items = self.0;
        let other_items = other.0;
        self_items.iter().enumerate().all(|(i, qty)| qty >= &other_items[i])
    }
}

impl PartialEq for Inventory {
    fn eq(&self, other: &Self) -> bool {
        let self_items = self.0;
        let other_items = other.0;
        self_items.iter().enumerate().all(|(i, qty)| qty == &other_items[i])
    }

    fn ne(&self, other: &Self) -> bool {
        !self.eq(other)
    }
}
