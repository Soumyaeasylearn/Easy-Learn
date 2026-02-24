-- ============================================================
-- Spoken English Coach — Supabase Schema
-- Run in Supabase SQL editor: https://app.supabase.com
-- ============================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ── profiles ────────────────────────────────────────────────
-- Linked to Supabase Auth (auth.users)
create table public.profiles (
  id                  uuid primary key references auth.users(id) on delete cascade,
  username            text,
  level               text not null default 'beginner'    -- beginner | intermediate | advanced
                        check (level in ('beginner','intermediate','advanced')),
  interests           text[]        default '{}',          -- e.g. ['business','travel']
  streak              int           default 0,
  last_active_date    date,
  completed_lessons   text[]        default '{}',          -- lesson IDs
  total_sessions      int           default 0,
  created_at          timestamptz   default now()
);

-- Auto-create profile on sign-up
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, username)
  values (new.id, new.raw_user_meta_data->>'name');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ── coaching_sessions ────────────────────────────────────────
create table public.coaching_sessions (
  id          bigserial primary key,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  transcript  text not null,
  correction  text,
  explanation text,
  score       smallint check (score between 1 and 10),
  tags        text[]     default '{}',         -- grammar | vocabulary | pronunciation | fluency
  created_at  timestamptz default now()
);

create index idx_sessions_user_id    on public.coaching_sessions(user_id);
create index idx_sessions_created_at on public.coaching_sessions(created_at desc);

-- ── lessons ──────────────────────────────────────────────────
create table public.lessons (
  id          text primary key,               -- e.g. 'g1', 'p2'
  title       text not null,
  area        text not null,                  -- grammar | pronunciation | vocabulary | fluency
  level       text not null default 'beginner',
  content     jsonb,                          -- structured lesson content
  created_at  timestamptz default now()
);

-- Seed core lessons
insert into public.lessons (id, title, area, level) values
  ('g1','Subject-Verb Agreement','grammar','beginner'),
  ('g2','Past Simple vs Present Perfect','grammar','intermediate'),
  ('g3','Conditional Sentences','grammar','advanced'),
  ('v1','Common Phrasal Verbs','vocabulary','beginner'),
  ('v2','Business English Vocabulary','vocabulary','intermediate'),
  ('v3','Idiomatic Expressions','vocabulary','advanced'),
  ('p1','Vowel Sounds Practice','pronunciation','beginner'),
  ('p2','Stress and Rhythm','pronunciation','intermediate'),
  ('p3','Connected Speech','pronunciation','advanced'),
  ('f1','Filler Words & Hesitations','fluency','beginner'),
  ('f2','Storytelling Techniques','fluency','intermediate'),
  ('f3','Debate & Persuasion','fluency','advanced');

-- ── Row Level Security ───────────────────────────────────────

alter table public.profiles         enable row level security;
alter table public.coaching_sessions enable row level security;
alter table public.lessons           enable row level security;

-- Profiles: users can only read/write their own row
create policy "users own profile"
  on public.profiles for all
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Sessions: users can only access their own sessions
create policy "users own sessions"
  on public.coaching_sessions for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Lessons: readable by everyone
create policy "lessons are public"
  on public.lessons for select
  using (true);

-- ── Streak maintenance function ──────────────────────────────
-- Called via Supabase Edge Function or cron to update streaks

create or replace function update_streak(p_user_id uuid)
returns void language plpgsql as $$
declare
  v_last_date date;
  v_today     date := current_date;
begin
  select last_active_date into v_last_date
  from public.profiles where id = p_user_id;

  if v_last_date = v_today then
    -- Already active today, no change
    return;
  elsif v_last_date = v_today - 1 then
    -- Consecutive day
    update public.profiles
    set streak = streak + 1, last_active_date = v_today,
        total_sessions = total_sessions + 1
    where id = p_user_id;
  else
    -- Streak broken
    update public.profiles
    set streak = 1, last_active_date = v_today,
        total_sessions = total_sessions + 1
    where id = p_user_id;
  end if;
end;
$$;
