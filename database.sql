-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.pens (
  id text NOT NULL,
  name text,
  user_id uuid DEFAULT auth.uid(),
  created_at timestamp with time zone DEFAULT now(),
  type text DEFAULT 'livestock'::text,
  CONSTRAINT pens_pkey PRIMARY KEY (id)
);
CREATE TABLE public.env_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  pen_id text,
  temperature double precision,
  humidity double precision,
  smell_level double precision DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT env_logs_pkey PRIMARY KEY (id),
  CONSTRAINT env_logs_pen_id_fkey FOREIGN KEY (pen_id) REFERENCES public.pens(id)
);
CREATE TABLE public.animals (
  id text NOT NULL,
  pen_id text,
  species text,
  weight double precision,
  target_weight double precision,
  feeding_status text DEFAULT 'Normal'::text,
  status text DEFAULT 'Khoe'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT animals_pkey PRIMARY KEY (id),
  CONSTRAINT animals_pen_id_fkey FOREIGN KEY (pen_id) REFERENCES public.pens(id)
);
CREATE TABLE public.devices (
  id text NOT NULL,
  pen_id text,
  name text,
  is_active boolean DEFAULT false,
  pin_number integer,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT devices_pkey PRIMARY KEY (id),
  CONSTRAINT devices_pen_id_fkey FOREIGN KEY (pen_id) REFERENCES public.pens(id)
);
CREATE TABLE public.health_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  animal_id text,
  type text,
  title text,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT health_logs_pkey PRIMARY KEY (id),
  CONSTRAINT health_logs_animal_id_fkey FOREIGN KEY (animal_id) REFERENCES public.animals(id)
);
CREATE TABLE public.weight_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  animal_id text,
  weight double precision,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT weight_logs_pkey PRIMARY KEY (id),
  CONSTRAINT weight_logs_animal_id_fkey FOREIGN KEY (animal_id) REFERENCES public.animals(id)
);
CREATE TABLE public.feed_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  pen_id text,
  food_name text,
  amount double precision,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT feed_logs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.usage_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid DEFAULT auth.uid(),
  item_name text,
  amount double precision,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT usage_logs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.inventory (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid DEFAULT auth.uid(),
  name text NOT NULL,
  category text DEFAULT 'Feed'::text,
  quantity double precision DEFAULT 0,
  unit text DEFAULT 'kg'::text,
  unit_price double precision DEFAULT 0,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT inventory_pkey PRIMARY KEY (id)
);
CREATE TABLE public.inventory_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid DEFAULT auth.uid(),
  item_name text,
  action_type text,
  amount double precision,
  pen_id text,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT inventory_logs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.crops (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  pen_id text,
  name text,
  quantity integer,
  plant_date date,
  harvest_date date,
  status text DEFAULT 'Growing'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT crops_pkey PRIMARY KEY (id),
  CONSTRAINT crops_pen_id_fkey FOREIGN KEY (pen_id) REFERENCES public.pens(id)
);
CREATE TABLE public.crop_growth_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  crop_id bigint,
  size double precision,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT crop_growth_logs_pkey PRIMARY KEY (id),
  CONSTRAINT crop_growth_logs_crop_id_fkey FOREIGN KEY (crop_id) REFERENCES public.crops(id)
);
CREATE TABLE public.crop_care_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  crop_id bigint,
  type text,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT crop_care_logs_pkey PRIMARY KEY (id),
  CONSTRAINT crop_care_logs_crop_id_fkey FOREIGN KEY (crop_id) REFERENCES public.crops(id)
);
CREATE TABLE public.field (
  id text NOT NULL,
  name text,
  user_id uuid DEFAULT auth.uid(),
  created_at timestamp with time zone DEFAULT now(),
  type text DEFAULT 'livestock'::text,
  CONSTRAINT field_pkey PRIMARY KEY (id)
);
CREATE TABLE public.media (
  id text NOT NULL,
  lesson text NOT NULL DEFAULT 'all'::text,
  lesson_title text,
  category text NOT NULL DEFAULT 'tac-pham'::text,
  title text NOT NULL,
  subtitle text,
  author text,
  source text,
  quote text,
  analysis text,
  tips text,
  type_label text,
  image_url text,
  video_url text,
  prompt text,
  tags ARRAY DEFAULT '{}'::text[],
  description text,
  likes integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT media_pkey PRIMARY KEY (id)
);
CREATE TABLE public.pending_contributions (
  id text NOT NULL,
  category text NOT NULL DEFAULT 'media'::text,
  section text NOT NULL DEFAULT '2'::text,
  lesson text DEFAULT 'all'::text,
  title text NOT NULL,
  author text,
  school text,
  quote text,
  analysis text,
  description text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text DEFAULT 'pending'::text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT pending_contributions_pkey PRIMARY KEY (id)
);
CREATE TABLE public.quiz_banks (
  id text NOT NULL,
  title text NOT NULL,
  subtitle text,
  subject text,
  time_minutes integer DEFAULT 15,
  total_questions integer DEFAULT 0,
  questions jsonb DEFAULT '[]'::jsonb,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT quiz_banks_pkey PRIMARY KEY (id)
);
CREATE TABLE public.documents (
  id text NOT NULL,
  type text NOT NULL DEFAULT 'powerpoint'::text,
  title text NOT NULL,
  subtitle text,
  grade text,
  author text,
  date text,
  pages text,
  format text,
  badge text,
  icon text,
  description text,
  file_url text,
  file_name text,
  online_url text,
  ppt_slides jsonb DEFAULT '[]'::jsonb,
  content_html text,
  download_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT documents_pkey PRIMARY KEY (id)
);
CREATE TABLE public.artworks (
  id text NOT NULL,
  title text NOT NULL,
  author text,
  school text,
  category text DEFAULT 'Hội họa'::text,
  medium text,
  dimensions text,
  image_url text,
  likes integer DEFAULT 0,
  badge text,
  description text,
  technique text,
  artist_note text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT artworks_pkey PRIMARY KEY (id)
);
CREATE TABLE public.lectures (
  id text NOT NULL,
  title text NOT NULL,
  subtitle text,
  author text,
  icon text DEFAULT '📚'::text,
  description text,
  video_url text,
  image_url text,
  web_url text,
  pdf_url text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT lectures_pkey PRIMARY KEY (id)
);