#![allow(dead_code)]

use std::cmp::{min, Ordering};
use std::ops::{Index, IndexMut, Mul, Add};
use core::fmt;

#[derive(Debug, Copy, Clone, Eq, PartialEq, Hash)]
pub enum Class {
    Log = 0,
    Fish,
    Fruit,
    Vegetable,
    Gem,
    Lootbox,
    Cookie,
    Part,
}

#[derive(Debug, Copy, Clone, Eq, PartialEq, Hash)]
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
    Bread,
    Potato,
    Carrot,
    CommonLootbox,
    UncommonLootbox,
    RareLootbox,
    EpicLootbox,
    EdgyLootbox,
    OmegaLootbox,
    GodlyLootbox,
    Cookie,
    WolfSkin,
    ZombieEye,
    UnicornHorn,
    MermaidHair,
    Chip,
    DragonScale,
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum Action {
    Upgrade,
    Dismantle(u64),
    Trade,
}

#[derive(Debug, Eq)]
pub struct Strategy{
    pub inventory: Inventory,
    actions: Vec<Action>,
}

impl Strategy {
    pub fn new(inventory: Inventory) -> Strategy {
        Strategy::from(inventory, Vec::new())
    }

    pub fn from(inventory: Inventory, vec: Vec<Action>) -> Strategy {
        Strategy{
            inventory,
            actions: vec,
        }
    }

    pub fn get_inventory(self) -> Inventory {
        self.inventory
    }

    pub fn get_actions(self) -> Vec<Action> {
        self.actions
    }

    pub fn add_action(self, action: Action) -> Strategy {
        let Strategy{ mut actions, inventory } = self;
        actions.push(action);
        Strategy{ actions, inventory }
    }

    pub fn extend_actions(self, vec: Vec<Action>) -> Strategy {
        let Strategy{ mut actions, inventory } = self;
        actions.extend(vec);
        Strategy{ actions, inventory }
    }

    pub fn merge(self, other: Strategy) -> Strategy {
        let mut actions = self.actions.clone();
        actions.extend(other.actions.clone());
        Strategy {
            inventory: other.inventory.clone(),
            actions: actions,
        }
    }

    pub fn trade(self, losing: &Name, gaining: &Name, qty: i128) -> Strategy {
        let target_qty = if qty < 0 { u64::MAX } else { qty as u64 };
        let (litem, mut lqty) = (Items[losing], self.inventory[losing]);
        let gitem = Items[gaining];
        let (Item(litem_cls, _, _), Item(gitem_cls, _, _)) = (litem, gitem);

        // panic for un-tradeable
        Item::guard_craftable(&litem_cls);

        if litem_cls == gitem_cls {
            return self
        } else if litem_cls != Class::Log && gitem_cls != Class::Log {
            return self.trade(losing, &Name::WoodenLog, -1)
                .trade(&Name::WoodenLog, gaining, target_qty as i128)
        }

        let Strategy {mut inventory, actions} = self;
        return match (litem_cls, gitem_cls) {
            (Class::Log, _) => {
                let mut gqty: u64 = 0;
                let mut total_cost: u64 = 0;
                let exchange_rate = TradeTable::rate_from_logs(inventory.area, &gitem_cls).denominator;
                while lqty / exchange_rate > 0 && gqty < target_qty {
                    gqty += 1;
                    lqty -= exchange_rate;
                    total_cost += exchange_rate;
                };
                inventory[losing] -= total_cost;
                inventory[gaining] += gqty;
                Strategy{ inventory, actions }
            },
            (_, Class::Log) => {
                let exchange_rate = TradeTable::rate_to_logs(inventory.area, &litem_cls).numerator;
                let exchange_qty = if target_qty < lqty { target_qty } else { lqty };
                inventory[losing] -= exchange_qty;
                inventory[gaining] += exchange_qty * exchange_rate;
                Strategy{ inventory, actions }
            },
            _ => { panic!("Other cases handled by if block.") }
        }
    }

    pub fn migrate(&self, start: &Class, end: &Class, mut max_dismantle: usize) -> Strategy {
        if start == end {
            return self.clone() // nothing to do
        }
        let base_idx = Items::first_of(start);
        max_dismantle = min(max_dismantle, Items::last_of(start) - base_idx);
        let Strategy{ mut actions, mut inventory } = self.clone();

        let mut idx = base_idx + max_dismantle;
        while idx > base_idx {
            actions.push(Action::Dismantle(inventory[idx]));
            let (_, qty) = Items[idx].dismantle(inventory[idx]);
            inventory[idx] = 0;
            idx -= 1;
            inventory[idx] += qty;
        }
        let result_idx = Items::first_of(end);
        Strategy{ actions, inventory }.trade(&Items[base_idx].1, &Items[result_idx].1, -1)
    }

    pub fn migrate_all(&self, to_class: &Class, max_steps: usize) -> Strategy {
        let strat = self.clone().migrate(&Class::Gem, to_class, max_steps);
        let strat = strat.migrate(&Class::Fish, to_class, max_steps);
        let strat = strat.migrate(&Class::Fruit, to_class, max_steps);
        let strat = strat.migrate(&Class::Log, to_class, max_steps);
        return strat
    }

    /// What this inventory should look like in the provided area
    /// given they user follows an optimal trading strategy
    pub fn future_version(&self, end: TradeArea) -> Strategy {
        let all = 10; // used as an indicator to dismantle all
        let mut new_strategy = match self.inventory.area {
            TradeTable::A3 => self.migrate_all(&Class::Fish, all),
            TradeTable::A5 => self.migrate_all(&Class::Fruit, all),
            TradeTable::A7 => self.migrate(&Class::Fruit, &Class::Log, all),
            TradeTable::A8 => {
                // dismantle tier 4 logs and fish (mega log and epic fish), get fruit
                let tier = 4;
                self.migrate(&Class::Log, &Class::Fruit, tier)
                    .migrate(&Class::Fish, &Class::Fruit, tier)
            },
            TradeTable::A9 => {
                // dismantle tier 2 logs and fruit (epic log and banana), get fish
                let tier = 2;
                self.migrate(&Class::Log, &Class::Fish, tier)
                    .migrate(&Class::Fruit, &Class::Fish, tier)
            },
            TradeTable::A10 => {
                self.migrate(&Class::Fruit, &Class::Log, all)
            },
            // Make sure nothing is in rubies and have things in logs as the universal currency
            TradeTable::A11 => self.migrate_all(&Class::Log, all),
            _ => self.clone()
        };
        let Strategy{ mut inventory, actions } = new_strategy;
        if let Some(inventory) = inventory.next_area() {
            return Strategy{ inventory, actions }.future_version(end)
        }
        Strategy{ inventory, actions }
    }
}

impl Clone for Strategy {

    fn clone(&self) -> Strategy {
        let Strategy{ inventory, actions } = self;
        Strategy{
            inventory: inventory.clone(),
            actions: actions.clone()
        }
    }
}

impl Ord for Strategy {
    fn cmp(&self, other: &Self) -> Ordering {
        let (v1, v2) = (self.inventory.log_value(), other.inventory.log_value());
        return if v1 == v2 {
            other.actions.len().cmp(&self.actions.len())
        } else {
            v1.cmp(&v2)
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
        let (v1, v2) = (self.inventory.log_value(), other.inventory.log_value());
        v1 == v2 && self.actions.len() == other.actions.len()
    }
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub struct Item(pub Class, pub Name, pub u32);
impl Item {
    pub fn dismantle_cost(start: usize, end: usize, result: u64) -> u64 {
        let decay_top: u64 = 4;
        let decay_bottom: u64 = 5;
        let decay_times = end - start;
        return result * decay_bottom.pow(decay_times as u32) / decay_top.pow(decay_times as u32) - result
    }

    pub fn is_craftable(&self) -> bool {
        let Item(class, _, _) = &self;
        match class {
            Class::Log => true,
            Class::Fish => true,
            Class::Fruit => true,
            Class::Gem => true,
            _ => false,
        }
    }

    fn guard_craftable(cls: &Class) {
        if !Items[Items::first_of(cls)].is_craftable() {
            panic!(format!("Class {:?} cannot be traded to or from.", cls))
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

    pub fn dismantle_to(&self, mut available: u64, to: &Name, mut amount: u64) -> (u64, u64) {
        let mut current_qty: u64 = 0;
        let Item(_, losing_name, _) = self;
        let start_idx = Items::index_of(&losing_name);
        let end_idx = Items::index_of(to);
        // one at a time, dismantle from the starting item tier
        // to the indicated item tier until either
        // we run out of the starting tier or we have
        // enough of the target tier
        while available != 0 && current_qty < amount  {
            let mut qty: u64 = 1;
            let mut idx = start_idx;
            let mut current_item = self.clone();
            while idx > end_idx {
                (current_item, qty) = current_item.dismantle(qty);
                idx -= 1;
            }
            current_qty += qty;
            available -= 1;
        }
        // (qty, remainder)
        (current_qty, available)
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

        let mut cost = &self.required_for_upgrade(to);

        // if the cost is too much, we
        // will only upgrade as much as possible
        // (there will be no wasted upgrades)
        if amount * cost > available {
            amount = available / cost;
        }
        // how much of the starting item we will spend
        let total_cost = amount * cost;
        let (mut item, mut cost, mut remainder) = (self.clone(), total_cost, 0 as  u64);
        for i in start..end {
            (item, cost, remainder) = Items[i].upgrade(cost);
            assert_eq!(remainder, 0);
        }
        // (target item, target item count, remainder)
        (item, amount, available - total_cost)
    }

    pub fn required_for_upgrade(&self, to: &Name) -> u64 {
        assert_eq!(self.0, Items[to].0); // must have same class
        let start = Items::index_of(&self.1);
        let end = Items::index_of(to);
        assert!(end > start); // must be an upgrade
        let mut cost = 1;
        for i in start..end {
            cost *= Items[i+1].2
        };
        cost as u64
    }

    pub fn logs_required_for_upgrade(&self, mut amount: u64, area: TradeArea) -> u64 {
        let Item(class, name, _) = self;
        let end_idx = Items::index_of(&name);
        let start_idx = Items::first_of(&class);
        let mut logs_required = 0;
        for _ in 0..amount {
            let mut required_per_item = 1;
            let mut idx = end_idx;
            while idx > start_idx {
                let Item(_, _, value_of_previous) = Items[idx];
                required_per_item *= value_of_previous;
                idx -= 1;
            }
            logs_required += required_per_item as u64;
        }
        if class == &Class::Log {
            return logs_required;
        }
        let exchange_rate = TradeTable::rate_from_logs(area, &class).denominator;
        logs_required * exchange_rate
    }
}

pub struct Items;
impl Items {
    pub const INV_SIZE: usize = 29;

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
        Item(Class::Vegetable, Name::Bread, 1),
        Item(Class::Vegetable, Name::Potato, 1),
        Item(Class::Vegetable, Name::Carrot, 1),
        Item(Class::Lootbox, Name::CommonLootbox, 1),
        Item(Class::Lootbox, Name::UncommonLootbox, 1),
        Item(Class::Lootbox, Name::RareLootbox, 1),
        Item(Class::Lootbox, Name::EpicLootbox, 1),
        Item(Class::Lootbox, Name::EdgyLootbox, 1),
        Item(Class::Lootbox, Name::OmegaLootbox, 1),
        Item(Class::Lootbox, Name::GodlyLootbox, 1),
        Item(Class::Cookie, Name::Cookie, 1),
        Item(Class::Part, Name::WolfSkin, 1),
        Item(Class::Part, Name::ZombieEye, 1),
        Item(Class::Part, Name::UnicornHorn, 1),
        Item(Class::Part, Name::MermaidHair, 1),
        Item(Class::Part, Name::Chip, 1),
        Item(Class::Part, Name::DragonScale, 1),
    ];

    pub fn index_of(name: &Name) -> usize {
        for i in 0..Items::INV_SIZE {
            let Item(_, _name, _) = Items[i];
            if _name == *name {
                return i
            }
        }
        return usize::MAX // not possible
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

impl Index<&Name> for Items {
    type Output = Item;
    fn index(&self, name: &Name) -> &Self::Output {
        &Items[Items::index_of(name)]
    }
}

#[non_exhaustive]
pub struct TradeTable;

pub struct ExchangeRate{pub numerator: u64, pub denominator: u64}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub struct TradeArea(usize, usize, usize, u8);

impl Index<&Class> for TradeArea {
    type Output = usize;
    fn index(&self, index: &Class) -> &Self::Output {
        match index {
            Class::Log => &1,
            Class::Fish => &self.0,
            Class::Fruit => &self.1,
            Class::Gem => &self.2,
            _ => { Item::guard_craftable(index); return &0 }
        }
    }
}

impl TradeTable {
    const NUM_AREAS: usize = 15;
    //          ratio of (fish, apple, ruby):log
    pub const A1: TradeArea = TradeArea(1, 0, 0, 1);
    pub const A2: TradeArea = TradeArea(1, 0, 0, 2);
    pub const A3: TradeArea = TradeArea(1, 3, 0, 3);
    pub const A4: TradeArea = TradeArea(2, 4, 0, 4);
    pub const A5: TradeArea = TradeArea(2, 4, 450, 5);
    pub const A6: TradeArea = TradeArea(3, 15, 675, 6);
    pub const A7: TradeArea = TradeArea(3, 15, 675, 7);
    pub const A8: TradeArea = TradeArea(3, 8, 675, 8);
    pub const A9: TradeArea = TradeArea(2, 12, 850, 9);
    pub const A10: TradeArea = TradeArea(3, 12, 500, 10);
    pub const A11: TradeArea = TradeArea(3, 8, 500, 11);
    pub const A12: TradeArea = TradeArea(3, 8, 350, 12);
    pub const A13: TradeArea = TradeArea(3, 8, 350, 13);
    pub const A14: TradeArea = TradeArea(3, 8, 350, 14);
    pub const A15: TradeArea = TradeArea(2, 4, 250, 15);
    const AREAS: [TradeArea; TradeTable::NUM_AREAS] = [
        TradeTable::A1, TradeTable::A2, TradeTable::A3, TradeTable::A4,
        TradeTable::A5, TradeTable::A6, TradeTable::A7, TradeTable::A8,
        TradeTable::A9, TradeTable::A10, TradeTable::A11, TradeTable::A12,
        TradeTable::A13, TradeTable::A14, TradeTable::A15,
    ];

    pub fn from_usize(area: usize) -> Option<TradeArea> {
        if area > 15 { None } else { Some(TradeTable[area - 1]) }
    }

    pub fn next_area(area: TradeArea) -> Option<TradeArea> {
        if area == TradeTable[TradeTable::AREAS.len() - 1] {
            None
        } else {
            let TradeArea(_, _, _, area_number) = area;
            // area numbers are one-indexed while
            // TradeTable::AREAS is zero-indexed
            Some(TradeTable[area_number as usize])
        }
    }

    pub fn rate_from_logs(area: TradeArea, to: &Class) -> ExchangeRate {
        return ExchangeRate{
            numerator: 1,
            denominator: area[to] as u64
        };
    }

    pub fn rate_to_logs(area: TradeArea, from: &Class) -> ExchangeRate {
        return ExchangeRate{
            numerator: area[from] as u64,
            denominator: 1
        };
    }
}

impl Index<usize> for TradeTable {
    type Output = TradeArea;

    fn index(&self, index: usize) -> &Self::Output {
        &TradeTable::AREAS[index]
    }
}

#[derive(Debug, Copy, Clone, Eq)]
pub struct Inventory {
    pub inventory: [u64; Items::INV_SIZE],
    area: TradeArea,
}

impl Index<usize> for Inventory {
    type Output = u64;
    fn index(&self, index: usize) -> &Self::Output {
        &self.inventory[index]
    }
}

impl Index<&Name> for Inventory {
    type Output = u64;
    fn index(&self, name: &Name) -> &Self::Output {
        &self.inventory[Items::index_of(name)]
    }
}

impl IndexMut<usize> for Inventory {
    fn index_mut(&mut self, index: usize) -> &mut Self::Output {
        &mut self.inventory[index]
    }
}

impl IndexMut<&Name> for Inventory {
    fn index_mut(&mut self, name: &Name) -> &mut Self::Output {
        &mut self.inventory[Items::index_of(name)]
    }
}

impl Inventory {
    pub fn new(area: TradeArea) -> Inventory {
        Inventory {
            inventory: [0; Items::INV_SIZE],
            area,
        }
    }

    pub fn from_vec(area: TradeArea, vec: Vec<(&Name, u64)>) -> Inventory {
        let mut inv = Inventory::new(area);
        for (&name, qty) in vec.iter() {
            inv[&name] = *qty;
        }
        inv
    }

    pub fn from_array(area: TradeArea, inv: [u64; Items::INV_SIZE]) -> Inventory {
        Inventory::from_vec(
            area,
            inv.iter().enumerate().map(|(idx, qty)| (&Items[idx].1, *qty)).collect()
        )
    }

    pub fn itemized(
        area: TradeArea,
        wooden_log: u64, epic_log: u64, super_log: u64, mega_log: u64, hyper_log: u64, ultra_log: u64,
        normie_fish: u64, golden_fish: u64, epic_fish: u64,
        apple: u64, banana: u64,
        ruby: u64,
        bread: u64, potato: u64, carrot: u64,
        common: u64, uncommon: u64, rare: u64, epic: u64, edgy: u64, omega: u64, godly: u64,
        cookie: u64,
        skin: u64, eye: u64, horn: u64, hair: u64, chip: u64, scale: u64,
    ) -> Inventory {
        Inventory{
            area,
            inventory: [
                wooden_log, epic_log, super_log, mega_log, hyper_log, ultra_log,
                normie_fish, golden_fish, epic_fish,
                apple, banana,
                ruby,
                bread, potato, carrot,
                common, uncommon, rare, epic, edgy, omega, godly, // lootboxes
                cookie, // cookie
                skin, eye, horn, hair, chip, scale // parts
            ]
        }
    }

    pub fn get_area(&self) -> TradeArea {
        self.area
    }

    pub fn next_area(mut self) -> Option<Self> {
        match TradeTable::next_area(self.area) {
            None => return None,
            Some(area) => self.area = area
        }
        Some(self.clone())
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
        for i in 0..Items::INV_SIZE {
            if self.inventory[i] != 0 {
                vec.push((Items[i], self.inventory[i]))
            }
        }
        vec
    }

    pub fn trade(self, losing: &Name, gaining: &Name, qty: i128) -> Inventory {
        Strategy::new(self.clone()).trade(losing, gaining, qty).get_inventory()
    }

    pub fn migrate(&self, start: &Class, end: &Class, mut max_dismantle: usize) -> Inventory {
        Strategy::new(self.clone()).migrate(start, end, max_dismantle).get_inventory()
    }

    pub fn migrate_all(&self, to_class: &Class, max_steps: usize) -> Inventory {
        Strategy::new(self.clone()).migrate_all(to_class, max_steps).get_inventory()
    }

    /// What this inventory should look like in the provided area
    /// given they user follows an optimal trading strategy
    pub fn future_version(&self, end: TradeArea) -> Inventory {
        Strategy::new(self.clone()).future_version(end).get_inventory()
    }

    /// Ultimate value in logs of the provided inventory
    pub fn log_value(&self) -> u64 {
        self.future_version(TradeTable::A10)[&Name::WoodenLog]
    }
}

impl Ord for Inventory {
    fn cmp(&self, other: &Self) -> Ordering {
        // this implementation results in unstable sorting.
        if self == other {return Ordering::Equal}
        if self > other {return Ordering::Greater}
        if self < other {return Ordering::Less}
        // if neither inventory has strictly more or less items,
        // they can be compared on log value.
        self.log_value().cmp(&other.log_value())
    }
}

impl PartialOrd for Inventory {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }

    fn lt(&self, other: &Self) -> bool {
        let self_items = self.inventory;
        let other_items = other.inventory;
        self_items.iter().enumerate().all(|(i, qty)| qty < &other_items[i])
    }

    fn le(&self, other: &Self) -> bool {
        let self_items = self.inventory;
        let other_items = other.inventory;
        self_items.iter().enumerate().all(|(i, qty)| qty <= &other_items[i])
    }

    fn gt(&self, other: &Self) -> bool {
        let self_items = self.inventory;
        let other_items = other.inventory;
        self_items.iter().enumerate().all(|(i, qty)| qty > &other_items[i])
    }

    fn ge(&self, other: &Self) -> bool {
        let self_items = self.inventory;
        let other_items = other.inventory;
        self_items.iter().enumerate().all(|(i, qty)| qty >= &other_items[i])
    }
}

impl PartialEq for Inventory {
    fn eq(&self, other: &Self) -> bool {
        let self_items = self.inventory;
        let other_items = other.inventory;
        self_items.iter().enumerate().all(|(i, qty)| qty == &other_items[i])
    }

    fn ne(&self, other: &Self) -> bool {
        !self.eq(other)
    }
}

impl Add for Inventory {
    type Output = Inventory;

    fn add(self, rhs: Self) -> Self::Output {
        let mut inv = self.clone();
        for (idx, amount) in rhs.inventory.into_iter().enumerate() {
            inv[idx] += amount;
        }
        inv
    }
}

impl Mul<usize> for Inventory {
    type Output = Inventory;

    fn mul(self, rhs: usize) -> Self::Output {
        let mut inv = self.clone();
        if rhs == 0 {
            return Inventory::new(self.get_area());
        }
        for _ in 0..(rhs - 1) {
            inv = inv + self.clone();
        }
        inv
    }
}

impl fmt::Display for Inventory {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut out = format!("Inventory{{\n");
        for (item, qty) in self.non_zero() {
            out = format!("{}\t{:?}: {},\n", out, item.1, qty)
        }
        write!(f, "{}}})", out)
    }
}
