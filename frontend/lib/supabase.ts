import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://sopqsxhuitqcmnvosjeq.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_PdB8mBs-zLvYDpEXP-ds4A_YSktC8lm';

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
