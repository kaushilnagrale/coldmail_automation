// === Jobright: Scroll + Email All Connections (FIXED) ===
(async () => {
  const n = 2; // ← scroll cycles
  const LOAD_WAIT = 30000;
  const delay = (ms) => new Promise(r => setTimeout(r, ms));
  const log = (msg) => console.log(`[Bot] ${msg}`);

  const scrollDiv = document.querySelector('#scrollableDiv');
  if (!scrollDiv) { log('❌ #scrollableDiv not found!'); return; }

  // ── Step 1: Scroll #scrollableDiv to load more jobs ──
  for (let i = 1; i <= n; i++) {
    log(`[${i}/${n}] Scrolling #scrollableDiv...`);
    const start = Date.now();
    while (Date.now() - start < 5000) {
      scrollDiv.scrollTop = scrollDiv.scrollHeight;
      await delay(200);
    }
    const count = document.querySelectorAll('.index_job-card__oqX1M').length;
    log(`  Jobs visible: ${count} | Waiting ${LOAD_WAIT/1000}s...`);
    await delay(LOAD_WAIT);
  }

  // ── Step 2: Collect all job card IDs (virtualized list) ──
  const getJobIds = () => [...document.querySelectorAll('.index_job-card__oqX1M')].map(c => c.id);
  const processedJobs = new Set();
  let totalEmailed = 0, totalSkipped = 0, jobsProcessed = 0;

  // Keep scrolling through virtualized list
  scrollDiv.scrollTop = 0;
  await delay(2000);

  let noNewJobsCount = 0;
  while (noNewJobsCount < 3) {
    const currentCards = [...document.querySelectorAll('.index_job-card__oqX1M')];
    let foundNew = false;

    for (const card of currentCards) {
      if (processedJobs.has(card.id)) continue;
      processedJobs.add(card.id);
      foundNew = true;
      jobsProcessed++;

      const title = card.querySelector('.index_job-title__Riiip')?.textContent || 'Unknown';
      const company = card.querySelector('.index_company-name__jnxCX')?.textContent || '';
      log(`\n=== Job ${jobsProcessed}: ${title} @ ${company} ===`);

      // Click on job card's main content area
      const clickTarget = card.querySelector('.index_front__O2BWV') 
        || card.querySelector('.index_job-card-main__zhEkE')
        || card;
      clickTarget.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      await delay(4000);

      // Expand all "View" connection categories
      const viewBtns = [...document.querySelectorAll('button')].filter(
        b => b.textContent.trim() === 'View' && b.offsetParent !== null
      );
      for (const vb of viewBtns) {
        vb.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        await delay(1500);
      }
      await delay(1000);

      // Find all mail icon buttons in the right panel
      const getMailBtns = () => [...document.querySelectorAll('img[alt="mail-icon"]')]
        .map(img => img.closest('button') || img.closest('[role="button"]') || img.parentElement)
        .filter(btn => btn && btn.offsetParent !== null);

      const mailBtns = getMailBtns();
      log(`  Found ${mailBtns.length} contacts with mail icons`);

      for (let i = 0; i < mailBtns.length; i++) {
        try {
          // Re-query each time since DOM changes
          const freshMailBtns = getMailBtns();
          if (i >= freshMailBtns.length) break;
          const mailBtn = freshMailBtns[i];

          log(`  [${i+1}/${mailBtns.length}] Clicking mail icon...`);

          // STEP A: Click the mail icon
          mailBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
          await delay(3000);

          // STEP B: Click "Connect Now" button (fetches email)
          const connectBtn = document.querySelector('#index_connect-button-id__MFFmL')
            || [...document.querySelectorAll('button')].find(b => 
                b.textContent.trim() === 'Connect Now' && b.offsetParent !== null);

          if (connectBtn) {
            connectBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            log(`    → Clicked "Connect Now" — waiting for email fetch...`);
            await delay(10000);
          } else {
            log(`    ⚠ No "Connect Now" found, checking for Start Email directly...`);
            await delay(2000);
          }

          // STEP C: Click "Start Email" button
          const startEmailBtn = document.querySelector('#index_email-helper-popup-action-btn-id__qXMIa')
            || document.querySelector('button.index_email-helper-popup-trigger-email-button__Jzejt')
            || [...document.querySelectorAll('button')].find(b => 
                b.textContent.trim() === 'Start Email' && b.offsetParent !== null);

          if (startEmailBtn) {
            startEmailBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            log(`    ✅ "Start Email" clicked!`);
            totalEmailed++;
            await delay(3000);
          } else {
            log(`    ⚠ "Start Email" not found — skipping`);
            totalSkipped++;
          }

          // STEP D: Close any open modals/popups
          const closeAll = () => {
            document.querySelectorAll('.ant-modal-close').forEach(x => x.click());
            document.querySelectorAll('.ant-drawer-close').forEach(x => x.click());
            const cancelBtn = [...document.querySelectorAll('button')].find(
              b => b.textContent.trim() === 'Cancel' && b.offsetParent !== null
            );
            if (cancelBtn) cancelBtn.click();
            document.dispatchEvent(new KeyboardEvent('keydown', {
              key: 'Escape', code: 'Escape', bubbles: true
            }));
          };
          closeAll();
          await delay(1000);
          closeAll(); // double close for nested modals
          await delay(2000);

        } catch (err) {
          log(`    ❌ Error: ${err.message}`);
          totalSkipped++;
          // Try to clean up
          document.querySelectorAll('.ant-modal-close').forEach(x => x.click());
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
          await delay(2000);
        }
      }

      await delay(3000);
    }

    if (!foundNew) {
      noNewJobsCount++;
      log(`No new jobs found (attempt ${noNewJobsCount}/3), scrolling more...`);
      scrollDiv.scrollTop += 500;
      await delay(3000);
    } else {
      noNewJobsCount = 0;
      // Scroll down to reveal next batch in virtualized list
      scrollDiv.scrollTop += 300;
      await delay(2000);
    }
  }

  log(`\n${'='.repeat(40)}`);
  log(`🎉 ALL DONE!`);
  log(`  📧 Emails sent: ${totalEmailed}`);
  log(`  ⏭ Skipped: ${totalSkipped}`);
  log(`  📋 Jobs processed: ${jobsProcessed}`);
  log(`${'='.repeat(40)}`);
})();