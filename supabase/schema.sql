-- Bleecker & Bloom: Supabase schema.
-- Run once in the Supabase dashboard: SQL Editor > New query > paste > Run.
-- Safe to re-run.

-- Product catalog: public, read-only for the app. Filled by `python -m supabase_seed`.
create table if not exists public.products (
    name        text primary key,
    category    text not null,
    description text not null,
    ingredients jsonb not null default '[]'::jsonb,
    price       numeric(6, 2) not null,
    rating      numeric(2, 1) not null default 0,
    image_url   text not null default '',
    sort_order  integer not null default 0
);

alter table public.products enable row level security;

drop policy if exists "Products are readable by everyone" on public.products;
create policy "Products are readable by everyone"
    on public.products for select
    to anon, authenticated
    using (true);

-- One saved conversation per customer (anonymous Supabase user).
-- Row Level Security is on with no policies, so only the API's secret key can read or write it.
create table if not exists public.chats (
    user_id    uuid primary key references auth.users (id) on delete cascade,
    messages   jsonb not null default '[]'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.chats enable row level security;

-- Placed orders, priced by the API from the menu. Also API-only.
create table if not exists public.orders (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    items      jsonb not null,
    total      numeric(8, 2) not null,
    created_at timestamptz not null default now()
);

create index if not exists orders_user_id_created_at_idx on public.orders (user_id, created_at desc);

alter table public.orders enable row level security;

-- Product photos bucket: public read. The seed script uploads with the secret key.
insert into storage.buckets (id, name, public)
values ('product-images', 'product-images', true)
on conflict (id) do update set public = true;
