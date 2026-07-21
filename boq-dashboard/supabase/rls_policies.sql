-- ====================================================================
-- Complete Permissive RLS Policies for Supabase BOQ System
-- Enables SELECT, INSERT, UPDATE on all tables for the anon role
-- ====================================================================

alter table projects enable row level security;
alter table drawings enable row level security;
alter table drawing_elements enable row level security;
alter table fajardo_factors enable row level security;
alter table base_prices enable row level security;
alter table backup_computations enable row level security;
alter table boq_checklist enable row level security;

-- Projects Policies
drop policy if exists "anon read projects" on projects;
drop policy if exists "anon insert projects" on projects;
drop policy if exists "anon update projects" on projects;
create policy "anon read projects" on projects for select using (true);
create policy "anon insert projects" on projects for insert with check (true);
create policy "anon update projects" on projects for update using (true) with check (true);

-- Drawings Policies
drop policy if exists "anon read drawings" on drawings;
drop policy if exists "anon insert drawings" on drawings;
drop policy if exists "anon update drawings" on drawings;
create policy "anon read drawings" on drawings for select using (true);
create policy "anon insert drawings" on drawings for insert with check (true);
create policy "anon update drawings" on drawings for update using (true) with check (true);

-- Drawing Elements Policies
drop policy if exists "anon read drawing_elements" on drawing_elements;
drop policy if exists "anon insert drawing_elements" on drawing_elements;
drop policy if exists "anon update drawing_elements" on drawing_elements;
create policy "anon read drawing_elements" on drawing_elements for select using (true);
create policy "anon insert drawing_elements" on drawing_elements for insert with check (true);
create policy "anon update drawing_elements" on drawing_elements for update using (true) with check (true);

-- Fajardo Factors Policies
drop policy if exists "anon read fajardo_factors" on fajardo_factors;
drop policy if exists "anon insert fajardo_factors" on fajardo_factors;
drop policy if exists "anon update fajardo_factors" on fajardo_factors;
create policy "anon read fajardo_factors" on fajardo_factors for select using (true);
create policy "anon insert fajardo_factors" on fajardo_factors for insert with check (true);
create policy "anon update fajardo_factors" on fajardo_factors for update using (true) with check (true);

-- Base Prices Policies
drop policy if exists "anon read base_prices" on base_prices;
drop policy if exists "anon insert base_prices" on base_prices;
drop policy if exists "anon update base_prices" on base_prices;
create policy "anon read base_prices" on base_prices for select using (true);
create policy "anon insert base_prices" on base_prices for insert with check (true);
create policy "anon update base_prices" on base_prices for update using (true) with check (true);

-- Backup Computations Policies
drop policy if exists "anon read backup_computations" on backup_computations;
drop policy if exists "anon insert backup_computations" on backup_computations;
drop policy if exists "anon update backup_computations" on backup_computations;
create policy "anon read backup_computations" on backup_computations for select using (true);
create policy "anon insert backup_computations" on backup_computations for insert with check (true);
create policy "anon update backup_computations" on backup_computations for update using (true) with check (true);

-- BOQ Checklist Policies
drop policy if exists "anon read boq_checklist" on boq_checklist;
drop policy if exists "anon insert boq_checklist" on boq_checklist;
drop policy if exists "anon update boq_checklist" on boq_checklist;
create policy "anon read boq_checklist" on boq_checklist for select using (true);
create policy "anon insert boq_checklist" on boq_checklist for insert with check (true);
create policy "anon update boq_checklist" on boq_checklist for update using (true) with check (true);
