/* Copyright (C) 2026 potemkin666. AI-Assisted. See COPYING. */
(() => {
  'use strict';
  const releaseRoot = 'https://github.com/potemkin666/DhampirOS/releases/';
  const assetURL = (value) => {
    try {
      const url = new URL(value);
      return url.href.startsWith(`${releaseRoot}download/`) &&
        !url.username && !url.password && !url.search && !url.hash ? url.href : null;
    } catch { return null; }
  };
  async function loadDownloads() {
    const response = await fetch('showcase/downloads.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Download catalogue unavailable');
    const release = await response.json();
    if (release.status !== 'published' || release.audit !== 'passed') return;
    const entries = ['iso', 'ova'].map((kind) => {
      const asset = release.assets?.[kind];
      if (!asset || !/^[a-f0-9]{64}$/.test(asset.sha256) ||
          !Number.isSafeInteger(asset.bytes) || asset.bytes < 300000000 ||
          !assetURL(asset.url) || !new URL(asset.url).pathname.endsWith(`.${kind}`)) {
        throw new Error('Incomplete verified release');
      }
      return { kind, asset };
    });
    const sums = assetURL(release.checksums);
    const report = assetURL(release.report);
    if (!sums || !report || !/^[a-f0-9]{40}$/.test(release.source_commit)) {
      throw new Error('Missing release evidence');
    }
    entries.forEach(({ kind, asset }) => {
      const card = document.querySelector(`[data-download="${kind}"]`);
      const link = document.createElement('a');
      link.className = 'download-button';
      link.href = assetURL(asset.url);
      link.textContent = `Download .${kind}`;
      card.querySelector('button').replaceWith(link);
      card.querySelector('.download-meta').textContent =
        `${release.version} / AMD64 / ${(asset.bytes / 1073741824).toFixed(2)} GiB`;
      const hash = card.querySelector('.download-hash');
      hash.hidden = false;
      hash.querySelector('code').textContent = asset.sha256;
    });
    const status = document.getElementById('download-status');
    status.textContent = release.tracker_findings_present ?
      'Experimental images for isolated VM testing. Vulnerability tracker findings remain in the report; review them before use.' :
      'Experimental alpha for VM testing. Read the verification report before using these images.';
    const evidence = document.getElementById('download-evidence');
    evidence.hidden = false;
    evidence.querySelector('[data-checksums]').href = sums;
    evidence.querySelector('[data-report]').href = report;
    evidence.querySelector('[data-source]').href =
      `https://github.com/potemkin666/DhampirOS/commit/${release.source_commit}`;
  }
  loadDownloads().catch(() => {
    document.getElementById('download-status').textContent =
      'Downloads are unavailable until the release and its verification evidence can be confirmed.';
  });
})();
