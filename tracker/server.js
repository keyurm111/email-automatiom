import express from 'express';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

const __dirname = path.resolve(); // needed for ES module

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// 1️⃣ Serve tracking pixel — with open_count logic
app.get('/track/open', async (req, res) => {
  const { email, uid } = req.query;

  try {
    // Check if there's already an open record for this email
    const { data, error: selectError } = await supabase
      .from('email_tracking')
      .select('*')
      .eq('email', email)
      .eq('type', 'open')
      .single();

    if (selectError && selectError.code !== 'PGRST116') {
      // Some other error (not 'no rows found')
      console.error('❌ Select error:', selectError);
    }

    if (data) {
      // Exists — increment open_count & update last_opened
      const { error: updateError } = await supabase
        .from('email_tracking')
        .update({
          open_count: data.open_count + 1,
          last_opened: new Date().toISOString(),
          ip: req.ip,
          user_agent: req.get('User-Agent')
        })
        .eq('id', data.id);

      if (updateError) console.error('❌ Update error:', updateError);
      else console.log(`🔄 Updated open_count for ${email}`);
    } else {
      // No row yet — insert new row
      const { error: insertError } = await supabase
        .from('email_tracking')
        .insert([{
          type: 'open',
          email,
          uid,
          open_count: 1,
          last_opened: new Date().toISOString(),
          ip: req.ip,
          user_agent: req.get('User-Agent')
        }]);

      if (insertError) console.error('❌ Insert error:', insertError);
      else console.log(`✅ Inserted first open for ${email}`);
    }

    res.sendFile(path.join(__dirname, 'pixel.png'));
  } catch (err) {
    console.error('❌ General error:', err);
    res.sendFile(path.join(__dirname, 'pixel.png'));
  }
});

// 2️⃣ Click tracking + redirect (unchanged, logs every click as new row)
app.get('/track/click', async (req, res) => {
  const { email, uid, redirect } = req.query;

  await supabase
    .from('email_tracking')
    .insert({
      type: 'click',
      email,
      uid,
      ip: req.ip,
      user_agent: req.get('User-Agent'),
      redirect_url: redirect,
      timestamp: new Date().toISOString()
    });

  console.log(`✅ Click logged for ${email}`);
  res.redirect(redirect);
});

// 3️⃣ Optional: view logs
app.get('/logs', async (req, res) => {
  const { data, error } = await supabase.from('email_tracking').select('*');
  if (error) return res.json({ error });
  res.json(data);
});

app.listen(port, () => {
  console.log(`🚀 Tracker running on http://localhost:${port}`);
});
