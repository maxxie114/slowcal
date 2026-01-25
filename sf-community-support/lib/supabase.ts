import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://lvlkgssnfmszujxtrasa.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx2bGtnc3NuZm1zenVqeHRyYXNhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzc3NjUxMDAsImV4cCI6MjA1MzM0MTEwMH0.sb_publishable_l8Cx8bsqkPZ-B_q3ka6MmQ_JspTcv30';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
