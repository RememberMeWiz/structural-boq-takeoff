-- ====================================================================
-- Automated Quantity Takeoff and Bill of Quantities (BOQ) System
-- Database Schema for Supabase (PostgreSQL)
-- Scoped for Phase 1: Concrete Works, Steel Reinforcement, and Masonry
-- SEED DATA CORRECTED to match Technical Specification v2.0 (§2.6)
-- ====================================================================

-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

-- 1. PROJECTS TABLE
create table projects (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text,
    created_at timestamptz default now() not null
);

-- 2. DRAWINGS TABLE
create table drawings (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid references projects(id) on delete cascade not null,
    filename text not null,
    sheet_ref text not null, -- e.g., 'S-1', 'A-2'
    scale_factor numeric default 1.0 not null,
    scale_confidence numeric check (scale_confidence >= 0 and scale_confidence <= 1),
    created_at timestamptz default now() not null
);

-- 3. DRAWING ELEMENTS (Drawing Object Model / DOM)
create table drawing_elements (
    id uuid primary key default uuid_generate_v4(),
    drawing_id uuid references drawings(id) on delete cascade not null,
    element_type text not null check (element_type in ('footing', 'column', 'beam', 'slab', 'chb_wall', 'other')),
    label text not null, -- e.g., 'C-1', '2B-2', 'F-1'
    geometry jsonb not null, -- { L: 1.2, W: 1.2, H: 0.4, Area: 1.44, count: 1 }
    concrete_class text check (concrete_class in ('Class AA', 'Class A', 'Class B', 'Class C', 'Thin Topping')),
    rebar_details jsonb, -- array of rebar specs: [ { diameter: 16, count: 8, length: 4500, spacing: 150 } ]
    raw_source text, -- DXF layer, vector coordinates info
    confidence numeric check (confidence >= 0 and confidence <= 1) default 1.0 not null,
    created_at timestamptz default now() not null
);

-- 4. FAJARDO FORMULA LIBRARY (Resource Ratios per Unit)
create table fajardo_factors (
    id serial primary key,
    trade_section text not null check (trade_section in ('Concrete Works', 'Steel Reinforcement', 'Masonry Works')),
    item_name text not null, -- e.g., 'Class A Concrete', '100mm CHB Wall', '16mm Plaster Face'
    resource_name text not null, -- e.g., 'Cement (40kg bags)', 'Sand (cu.m.)', 'Gravel (cu.m.)', 'CHB (pcs)'
    ratio_per_unit numeric not null, -- factor per cu.m. (concrete) or per sq.m. (masonry/plaster) or per meter (rebar weight)
    unit text not null, -- e.g., 'bag', 'cu.m.', 'pc', 'kg'
    created_at timestamptz default now() not null
);

-- 5. UNIT COST DERIVATION (Regional Base Prices)
create table base_prices (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid references projects(id) on delete cascade not null,
    resource_name text not null,
    unit text not null,
    unit_cost numeric not null check (unit_cost >= 0),
    updated_at timestamptz default now() not null,
    unique (project_id, resource_name)
);

-- 6. BACK-UP COMPUTATION SCHEMA (Takeoff Elements Detail)
create table backup_computations (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid references projects(id) on delete cascade not null,
    element_id uuid references drawing_elements(id) on delete set null,
    work_section text not null check (work_section in ('Concrete Works', 'Steel Reinforcement', 'Masonry Works')),
    item_code text not null, -- e.g., 'CON-2.1', 'MAS-3.2', 'REB-4.1'
    location_description text not null, -- e.g., 'Footing F-1 at Grid B-3'
    drawing_ref text not null, -- e.g., 'S-1 structural p.29'
    l_or_area numeric not null check (l_or_area >= 0),
    w numeric not null default 1.0 check (w >= 0),
    h_or_t numeric not null default 1.0 check (h_or_t >= 0),
    no numeric not null default 1.0 check (no >= 0),
    quantity numeric not null check (quantity >= 0),
    unit text not null,
    unit_cost numeric not null default 0.0 check (unit_cost >= 0),
    amount numeric generated always as (quantity * unit_cost) stored,
    status text not null check (status in ('Confirmed', 'Surveyed', 'N/A', 'Included in other item')),
    created_at timestamptz default now() not null
);

-- 7. ITEMIZED CHECKLIST / BOQ SUMMARY
create table boq_checklist (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid references projects(id) on delete cascade not null,
    item_no text not null,
    item_code text not null,
    description text not null,
    unit text not null,
    qty numeric not null default 0.0 check (qty >= 0),
    unit_cost numeric not null default 0.0 check (unit_cost >= 0),
    amount numeric generated always as (qty * unit_cost) stored,
    status text not null check (status in ('Confirmed', 'Surveyed', 'N/A')),
    created_at timestamptz default now() not null,
    unique (project_id, item_code)
);

-- ====================================================================
-- SEED DATA (Fajardo Mix Factors — corrected to match Tech Spec v2.0 §2.6)
-- ====================================================================

-- 4.1 Concrete Mix Designs (per 1 cu.m., 40kg cement bags — Option A, §2.6.1)
insert into fajardo_factors (trade_section, item_name, resource_name, ratio_per_unit, unit) values
('Concrete Works', 'Class AA Concrete', 'Cement (40kg bags)', 12.00, 'bag'),
('Concrete Works', 'Class AA Concrete', 'Sand (cu.m.)',        0.50, 'cu.m.'),
('Concrete Works', 'Class AA Concrete', 'Gravel (cu.m.)',      1.00, 'cu.m.'),
('Concrete Works', 'Class A Concrete',  'Cement (40kg bags)',  9.00, 'bag'),
('Concrete Works', 'Class A Concrete',  'Sand (cu.m.)',        0.50, 'cu.m.'),
('Concrete Works', 'Class A Concrete',  'Gravel (cu.m.)',      1.00, 'cu.m.'),
('Concrete Works', 'Class B Concrete',  'Cement (40kg bags)',  7.50, 'bag'),
('Concrete Works', 'Class B Concrete',  'Sand (cu.m.)',        0.50, 'cu.m.'),
('Concrete Works', 'Class B Concrete',  'Gravel (cu.m.)',      1.00, 'cu.m.'),
('Concrete Works', 'Class C Concrete',  'Cement (40kg bags)',  6.00, 'bag'),
('Concrete Works', 'Class C Concrete',  'Sand (cu.m.)',        0.50, 'cu.m.'),
('Concrete Works', 'Class C Concrete',  'Gravel (cu.m.)',      1.00, 'cu.m.');

-- 4.2 CHB Laying Mortar & Cell Fill per 1 sq.m. wall (Class B mortar default, §2.6.3)
insert into fajardo_factors (trade_section, item_name, resource_name, ratio_per_unit, unit) values
('Masonry Works', '100mm (4") CHB Wall', 'CHB (pcs)',           12.5,   'pc'),
('Masonry Works', '100mm (4") CHB Wall', 'Cement (40kg bags)',  0.522,  'bag'),
('Masonry Works', '100mm (4") CHB Wall', 'Sand (cu.m.)',        0.0435, 'cu.m.'),
('Masonry Works', '150mm (6") CHB Wall', 'CHB (pcs)',           12.5,   'pc'),
('Masonry Works', '150mm (6") CHB Wall', 'Cement (40kg bags)',  1.01,   'bag'),
('Masonry Works', '150mm (6") CHB Wall', 'Sand (cu.m.)',        0.084,  'cu.m.');

-- 4.3 Plastering per 1 sq.m. wall surface, 16mm thick, Class B plaster (§2.6.3)
insert into fajardo_factors (trade_section, item_name, resource_name, ratio_per_unit, unit) values
('Masonry Works', '16mm Plaster (1 face)',  'Cement (40kg bags)', 0.192, 'bag'),
('Masonry Works', '16mm Plaster (1 face)',  'Sand (cu.m.)',       0.016, 'cu.m.'),
('Masonry Works', '16mm Plaster (2 faces)', 'Cement (40kg bags)', 0.384, 'bag'),
('Masonry Works', '16mm Plaster (2 faces)', 'Sand (cu.m.)',       0.032, 'cu.m.');

-- 4.4 Rebar Theoretical Unit Weights, PNS 49 / ASTM A615, kg per linear meter (§2.6.2)
insert into fajardo_factors (trade_section, item_name, resource_name, ratio_per_unit, unit) values
('Steel Reinforcement', 'Ø10mm Rebar', 'Weight (kg/m)', 0.617, 'kg'),
('Steel Reinforcement', 'Ø12mm Rebar', 'Weight (kg/m)', 0.888, 'kg'),
('Steel Reinforcement', 'Ø16mm Rebar', 'Weight (kg/m)', 1.578, 'kg'),
('Steel Reinforcement', 'Ø20mm Rebar', 'Weight (kg/m)', 2.466, 'kg'),
('Steel Reinforcement', 'Ø25mm Rebar', 'Weight (kg/m)', 3.853, 'kg'),
('Steel Reinforcement', 'Ø28mm Rebar', 'Weight (kg/m)', 4.834, 'kg'),
('Steel Reinforcement', 'Ø32mm Rebar', 'Weight (kg/m)', 6.313, 'kg');

-- 4.5 G.I. Tie Wire Factor — general ratio per kg rebar (§2.6.2)
insert into fajardo_factors (trade_section, item_name, resource_name, ratio_per_unit, unit) values
('Steel Reinforcement', 'Rebar Works', 'Tie Wire #16 G.I. (per kg rebar)', 0.015, 'kg');

-- ====================================================================
-- VIEWS AND TRIGGERS FOR ROLLUP CONSOLIDATION
-- ====================================================================

create or replace view view_backup_rollup as
select
    project_id,
    item_code,
    sum(quantity) as rolled_qty,
    case
        when sum(quantity) > 0 then sum(amount) / sum(quantity)
        else 0.0
    end as blended_unit_cost
from backup_computations
group by project_id, item_code;

create index idx_drawings_project_id on drawings(project_id);
create index idx_elements_drawing_id on drawing_elements(drawing_id);
create index idx_backup_project_id on backup_computations(project_id);
create index idx_backup_item_code on backup_computations(item_code);
create index idx_boq_project_id on boq_checklist(project_id);
create index idx_boq_item_code on boq_checklist(item_code);
