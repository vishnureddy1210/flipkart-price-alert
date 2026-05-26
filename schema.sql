-- =============================================
-- Flipkart Price Alert — Supabase Schema
-- Run this in: Supabase → SQL Editor → New Query
-- =============================================


-- Products table: stores what we are tracking
create table products (
  id            bigint generated always as identity primary key,
  url           text not null,
  name          text not null,
  target_price  integer not null,       -- in rupees, e.g. 45000
  active        boolean default true,
  created_at    timestamptz default now()
);

-- Price history table: one row per check
create table price_history (
  id          bigint generated always as identity primary key,
  product_id  bigint references products(id) on delete cascade,
  price       integer not null,         -- in rupees
  checked_at  timestamptz default now()
);

-- Index to speed up history lookups
create index idx_price_history_product
  on price_history(product_id, checked_at desc);


-- =============================================
-- Sample data to test with
-- =============================================

insert into products (url, name, target_price) values
  (
    'https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4',
    'Apple iPhone 15 (Black, 128 GB)',
    65000
  );