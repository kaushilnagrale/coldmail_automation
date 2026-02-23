// === Jobright: Scroll + Custom Resume + Email All Connections ===
(async () => {
  const n = 4;
  const LOAD_WAIT = 3000;
  const delay = (ms) => new Promise(r => setTimeout(r, ms));
  const log = (msg) => console.log(`[Bot] ${msg}`);

  // Multi-strategy click that works with React/Ant Design
  const forceClick = (el) => {
    if (!el) return false;
    // Method 1: Native click
    el.click();
    // Method 2: MouseEvent dispatch
    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    // Method 3: PointerEvent (React 17+ uses these)
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
    el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
    return true;
  };

  const scrollDiv = document.querySelector('#scrollableDiv');
  if (!scrollDiv) { log('❌ #scrollableDiv not found!'); return; }

  // ── Step 1: Scroll to load jobs ──
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

  // ── Step 2: Process jobs ──
  const processedJobs = new Set();
  let totalEmailed = 0, totalSkipped = 0, totalResumes = 0, jobsProcessed = 0;

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
      log(`\n${'='.repeat(50)}`);
      log(`Job ${jobsProcessed}: ${title} @ ${company}`);
      log(`${'='.repeat(50)}`);

      // Click job card
      const clickTarget = card.querySelector('.index_front__O2BWV')
        || card.querySelector('.index_job-card-main__zhEkE') || card;
      forceClick(clickTarget);
      await delay(4000);

      // ════════════════════════════════════════
      // PHASE A: CUSTOM RESUME
      // ════════════════════════════════════════
      try {
        log(`  📄 [Resume] Starting...`);

        // A1: "View Custom Resume"
        const viewResumeBtn = document.querySelector('#index_tailorResumeBannerId__4h2HZ button')
          || document.querySelector('.index_viewTailorResumeBtn__m2_Gt')
          || [...document.querySelectorAll('button')].find(b =>
              b.textContent.includes('View Custom Resume') && b.offsetParent !== null);
        if (viewResumeBtn) {
          forceClick(viewResumeBtn);
          log(`    → Clicked "View Custom Resume"`);
          await delay(4000);
        } else {
          throw new Error('No "View Custom Resume" button');
        }

        // A2: Click 3rd button in overlay
        const overlayDivs = [...document.querySelectorAll('body > div')].filter(
          d => d.querySelector('.ant-modal, .ant-drawer, .ant-popover') && d.offsetParent !== null
        );
        let thirdBtn = null;
        if (overlayDivs.length > 0) {
          const lastOverlay = overlayDivs[overlayDivs.length - 1];
          const btns = [...lastOverlay.querySelectorAll('button')].filter(b => b.offsetParent !== null);
          if (btns.length >= 3) thirdBtn = btns[2];
        }
        if (thirdBtn) {
          forceClick(thirdBtn);
          log(`    → Clicked 3rd overlay button`);
          await delay(3000);
        }

        // A3: Click submit container button
        const submitBtn = document.querySelector('#index_resume-align-submit-container__ofqzS button');
        if (submitBtn) {
          forceClick(submitBtn);
          log(`    → Clicked submit container button`);
          await delay(2000);
        }

        // A4: Select "Full Edit" radio
        const fullEditRadio = document.querySelector('input[type="radio"][value="full"]');
        if (fullEditRadio) {
          const label = fullEditRadio.closest('label');
          if (label) forceClick(label);
          else forceClick(fullEditRadio);
          log(`    → Selected "Full Edit"`);
          await delay(1500);
        }

        // A5: "Unselect all"
        const unselectBtn = document.querySelector('.index_selectAllButton__a1r_y')
          || [...document.querySelectorAll('button')].find(b =>
              b.textContent.trim() === 'Unselect all' && b.offsetParent !== null);
        if (unselectBtn) {
          forceClick(unselectBtn);
          log(`    → Clicked "Unselect all"`);
          await delay(1500);
        }

        // A6: "Generate My New Resume"
        const generateBtn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.includes('Generate My New Resume') && b.offsetParent !== null);
        if (generateBtn) {
          forceClick(generateBtn);
          log(`    → "Generate My New Resume" — waiting 30s...`);
          await delay(30000);
        }

        // A7: "Download by PDF"
        const downloadBtn = document.querySelector('.index_download-button__qaBr8')
          || [...document.querySelectorAll('button')].find(b =>
              b.textContent.includes('Download by PDF') && b.offsetParent !== null);
        if (downloadBtn) {
          forceClick(downloadBtn);
          log(`    ✅ Resume downloaded as kaushil_nagrale.pdf`);
          totalResumes++;
          await delay(3000);
        }

        // Close resume modal
        document.querySelectorAll('.ant-modal-close, .ant-drawer-close').forEach(x => x.click());
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        await delay(2000);

      } catch (resumeErr) {
        log(`    ⚠ Resume skipped: ${resumeErr.message}`);
        document.querySelectorAll('.ant-modal-close, .ant-drawer-close').forEach(x => x.click());
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        await delay(2000);
      }

      // ════════════════════════════════════════
      // PHASE B: EMAIL CONNECTIONS
      // ════════════════════════════════════════
      log(`  📧 [Email] Starting...`);

      // Re-click job card
      forceClick(clickTarget);
      await delay(3000);

      // Expand "View" categories
      const viewBtns = [...document.querySelectorAll('button')].filter(
        b => b.textContent.trim() === 'View' && b.offsetParent !== null);
      for (const vb of viewBtns) { forceClick(vb); await delay(1500); }
      await delay(1000);

      const getMailBtns = () => [...document.querySelectorAll('img[alt="mail-icon"]')]
        .map(img => img.closest('button') || img.closest('[role="button"]') || img.parentElement)
        .filter(btn => btn && btn.offsetParent !== null);

      const mailBtns = getMailBtns();
      log(`  Found ${mailBtns.length} contacts`);

      for (let i = 0; i < mailBtns.length; i++) {
        try {
          const fresh = getMailBtns();
          if (i >= fresh.length) break;

          log(`  [${i+1}/${mailBtns.length}] Processing contact...`);

          // B1: Mail icon
          forceClick(fresh[i]);
          log(`    → Clicked mail icon`);
          await delay(3000);

          // B2: "Connect Now"
          const connectBtn = document.querySelector('#index_connect-button-id__MFFmL')
            || [...document.querySelectorAll('button')].find(b =>
                b.textContent.trim() === 'Connect Now' && b.offsetParent !== null);
          if (connectBtn) {
            forceClick(connectBtn);
            log(`    → Clicked "Connect Now" — waiting 10s for email fetch...`);
            await delay(10000);
          } else {
            log(`    ⚠ No "Connect Now"`);
            await delay(2000);
          }

          // B3: "Start Email" — ENHANCED CLICK
          let startEmailClicked = false;

          // Try 1: Direct ID
          let startBtn = document.getElementById('index_email-helper-popup-action-btn-id__qXMIa');
          if (startBtn && startBtn.offsetParent !== null) {
            log(`    → Found Start Email by ID`);
            forceClick(startBtn);
            startEmailClicked = true;
          }

          // Try 2: Class selector
          if (!startEmailClicked) {
            startBtn = document.querySelector('.index_email-helper-popup-trigger-email-button__Jzejt');
            if (startBtn && startBtn.offsetParent !== null) {
              log(`    → Found Start Email by class`);
              forceClick(startBtn);
              startEmailClicked = true;
            }
          }

          // Try 3: Text match
          if (!startEmailClicked) {
            startBtn = [...document.querySelectorAll('button')].find(b =>
              b.textContent.trim() === 'Start Email' && b.offsetParent !== null);
            if (startBtn) {
              log(`    → Found Start Email by text`);
              forceClick(startBtn);
              startEmailClicked = true;
            }
          }

          // Try 4: Click the <span> inside the button directly
          if (!startEmailClicked) {
            const span = [...document.querySelectorAll('button span')].find(s =>
              s.textContent.trim() === 'Start Email' && s.offsetParent !== null);
            if (span) {
              log(`    → Found Start Email span`);
              forceClick(span);
              forceClick(span.closest('button'));
              startEmailClicked = true;
            }
          }

          // Try 5: XPath as last resort
          if (!startEmailClicked) {
            try {
              const xpathResult = document.evaluate(
                "//button[span[text()='Start Email']]",
                document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
              );
              const xpathBtn = xpathResult.singleNodeValue;
              if (xpathBtn) {
                log(`    → Found Start Email by XPath`);
                forceClick(xpathBtn);
                startEmailClicked = true;
              }
            } catch(e) {}
          }

          if (startEmailClicked) {
            log(`    ✅ "Start Email" clicked — Outlook should open with draft!`);
            totalEmailed++;
            await delay(5000); // Extra time for Outlook to open
          } else {
            log(`    ❌ "Start Email" NOT FOUND after all attempts`);
            totalSkipped++;
          }

          // B4: Close modals
          const closeAll = () => {
            document.querySelectorAll('.ant-modal-close').forEach(x => x.click());
            document.querySelectorAll('.ant-drawer-close').forEach(x => x.click());
            const cancelBtn = [...document.querySelectorAll('button')].find(
              b => b.textContent.trim() === 'Cancel' && b.offsetParent !== null);
            if (cancelBtn) cancelBtn.click();
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
          };
          closeAll(); await delay(1000);
          closeAll(); await delay(2000);

        } catch (err) {
          log(`    ❌ Error: ${err.message}`);
          totalSkipped++;
          document.querySelectorAll('.ant-modal-close').forEach(x => x.click());
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
          await delay(2000);
        }
      }
      await delay(3000);
    }

    if (!foundNew) {
      noNewJobsCount++;
      scrollDiv.scrollTop += 500;
      await delay(3000);
    } else {
      noNewJobsCount = 0;
      scrollDiv.scrollTop += 300;
      await delay(2000);
    }
  }

  log(`\n${'='.repeat(50)}`);
  log(`🎉 ALL DONE!`);
  log(`  📄 Resumes: ${totalResumes} (saved as kaushil_nagrale.pdf)`);
  log(`  📧 Emails: ${totalEmailed}`);
  log(`  ⏭ Skipped: ${totalSkipped}`);
  log(`  📋 Jobs: ${jobsProcessed}`);
  log(`${'='.repeat(50)}`);
})();