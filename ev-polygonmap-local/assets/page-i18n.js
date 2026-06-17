window.EVPageI18n = (function () {
  const COMMON = {
    th: { back: '← กลับ', privacy: 'นโยบายความเป็นส่วนตัว', terms: 'ข้อกำหนดการใช้งาน', map: 'กลับหน้าแผนที่' },
    en: { back: '← Back', privacy: 'Privacy Policy', terms: 'Terms of Service', map: 'Back to map' },
    zh: { back: '← 返回', privacy: '隐私政策', terms: '服务条款', map: '返回地图' },
  };

  const PAGES = {
    about: {
      en: {
        title: 'About us — EV Stations Thailand',
        eyebrow: 'About us',
        heroTitle: 'EV Stations Thailand',
        tagline: 'A comprehensive EV charging station data platform for Thailand.',
        stats: ['charging stations nationwide', 'leading providers', 'provinces across Thailand'],
        missionTitle: 'Our mission',
        mission: 'We believe easy access to accurate charging-station information is essential for EV adoption in Thailand.\n\nEV Stations Thailand brings together data from leading providers including PTT EV Station, Spark / BCP, and iGreen+, covering more than 1,800 stations nationwide.',
        providersTitle: 'Included providers',
        providersBody: 'Charging station data from major providers in Thailand.',
        stationLabel: 'stations',
        contactTitle: 'Contact us',
        ctaTitle: 'Help improve the database',
        ctaBody: 'Know a charging station that is missing, or want to be part of Thailand\'s EV network?',
        addInfo: '🗺️ Submit station info',
        interested: '⚡ Build a station',
      },
      zh: {
        title: '关于我们 — EV Stations Thailand',
        eyebrow: '关于我们',
        heroTitle: 'EV Stations Thailand',
        tagline: '泰国电动车充电站数据平台，集中展示全国充电站信息。',
        stats: ['全国充电站', '主要运营商', '覆盖泰国府区'],
        missionTitle: '我们的使命',
        mission: '我们相信，准确、完整、易访问的充电站信息，是推动泰国电动车普及的重要基础。\n\nEV Stations Thailand 汇总 PTT EV Station、Spark / BCP、iGreen+ 等主要运营商的数据，覆盖全国 1,800 多个充电站。',
        providersTitle: '已收录运营商',
        providersBody: '收录泰国主要充电服务运营商的站点数据。',
        stationLabel: '个站点',
        contactTitle: '联系我们',
        ctaTitle: '一起完善数据库',
        ctaBody: '发现系统中缺失的充电站，或希望参与泰国 EV 充电网络建设？',
        addInfo: '🗺️ 提交站点信息',
        interested: '⚡ 建设充电站',
      },
    },

    interested: {
      en: {
        title: 'Build an EV charging station — EV Stations Thailand',
        heroTitle: 'Interested in building an EV charging station?',
        heroBody: 'We welcome operators, land owners, venue owners, and investors who want to expand Thailand\'s EV charging network.',
        benefits: [
          ['Good location', 'Add value to your property with modern EV charging service.'],
          ['Additional revenue', 'Generate charging-service revenue around the clock.'],
          ['Cleaner mobility', 'Support cleaner travel and reduce air pollution.'],
          ['Growing market', 'EV adoption in Thailand is rising, and charging demand grows every year.'],
        ],
        formTitle: 'Register your interest',
        subtitle: 'Leave your details and our team will contact you. Registration is free.',
        required: '<span class="required-star">*</span> Required',
        labels: ['Full name <span class="required-star">*</span>', 'Phone number <span class="required-star">*</span>', 'Email', 'Province of interest', 'Interest type', 'Additional details'],
        provincePlaceholder: 'e.g. Bangkok, Chonburi',
        radios: ['🏢 Land / venue owner', '💼 Investor', '🏪 Business operator', '✨ Other'],
        detailsPlaceholder: 'Property type, parking size, expected charger count, or anything else useful.',
        submit: 'Submit ✓',
        thanksTitle: 'Thank you for your interest!',
        thanksBody: 'We have received your information. Our team will contact you within 3-5 business days.',
        errors: { name: 'Please enter your full name', phone: 'Please enter your phone number', generic: 'Something went wrong. Please try again.' },
      },
      zh: {
        title: '建设 EV 充电站 — EV Stations Thailand',
        heroTitle: '有兴趣一起建设 EV 充电站吗？',
        heroBody: '我们欢迎运营商、场地业主、土地业主和投资人，一起扩展泰国电动车充电网络。',
        benefits: [
          ['优质位置', '用现代化 EV 充电服务提升场地价值。'],
          ['增加收入', '通过 24 小时充电服务创造额外收入。'],
          ['绿色出行', '支持清洁交通，减少空气污染。'],
          ['市场增长', '泰国 EV 保有量持续增长，充电需求逐年上升。'],
        ],
        formTitle: '登记合作意向',
        subtitle: '填写资料后，我们会与你联系。登记不收取费用。',
        required: '<span class="required-star">*</span> 必填',
        labels: ['姓名 <span class="required-star">*</span>', '电话 <span class="required-star">*</span>', '邮箱', '感兴趣的府/省', '合作类型', '补充说明'],
        provincePlaceholder: '例如：曼谷、春武里',
        radios: ['🏢 土地 / 场地业主', '💼 投资人', '🏪 商业运营者', '✨ 其他'],
        detailsPlaceholder: '例如场地情况、停车位数量、期望充电头数量或其他信息。',
        submit: '提交 ✓',
        thanksTitle: '感谢你的合作意向！',
        thanksBody: '我们已收到你的信息，团队会在 3-5 个工作日内联系你。',
        errors: { name: '请填写姓名', phone: '请填写电话', generic: '提交失败，请再试一次。' },
      },
    },

    addInfo: {
      en: {
        title: 'Submit charging station info — EV Stations Thailand',
        heroTitle: 'Submit charging station information',
        heroBody: 'Help make Thailand\'s EV charging database more complete and accurate. Submit a new station or correct existing information.',
        formTitle: 'Station information form',
        subtitle: 'Submitted information will be reviewed before it appears on the site.',
        required: '<span class="required-star">*</span> Required',
        sectionLabels: ['Submission type', 'Station information', 'Charger information (if known)', 'Reporter information (optional)'],
        typeNames: ['Add new station', 'Correct existing info'],
        typeDescs: ['A station that is not yet in the system', 'Update a station already in the system'],
        labels: ['Station name <span class="required-star">*</span>', 'Address / place', 'Province <span class="required-star">*</span>', 'District', 'DC heads', 'Day price', 'Night price', 'AC heads', 'Day price', 'Night price', 'Reporter name', 'Phone / email for follow-up', 'Additional notes'],
        placeholders: ['e.g. PTT EV Station Sathorn, WEH Charging Asok', 'e.g. B1 floor, building..., road...', 'e.g. Bangkok', 'e.g. Watthana, Bang Rak', 'e.g. 2', 'e.g. 7.50', 'e.g. 5.50', 'e.g. 4', 'e.g. 7.50', 'e.g. 5.50', 'Opening hours, fees, required app, or other useful details...'],
        dc: '⚡ Has DC fast charger',
        ac: '🔌 Has AC charger',
        submit: 'Submit ✓',
        thanksTitle: 'Thank you for improving the system!',
        thanksBody: 'Your information has been sent for review and will be added as soon as possible.',
        another: 'Submit more information',
        errors: { station: 'Please enter station name', province: 'Please enter province', generic: 'Something went wrong. Please try again.' },
      },
      zh: {
        title: '提交充电站信息 — EV Stations Thailand',
        heroTitle: '提交充电站信息',
        heroBody: '帮助泰国 EV 充电站数据库更完整、更准确。你可以提交新站点，也可以修正已有信息。',
        formTitle: '站点信息表单',
        subtitle: '提交的信息会先由团队审核，再加入系统。',
        required: '<span class="required-star">*</span> 必填',
        sectionLabels: ['提交类型', '站点信息', '充电头信息（如已知）', '提交人信息（选填）'],
        typeNames: ['新增站点', '修正信息'],
        typeDescs: ['系统中尚未收录的站点', '修正系统中已有站点的信息'],
        labels: ['站点名称 <span class="required-star">*</span>', '地址 / 地点', '府 / 省 <span class="required-star">*</span>', '区 / 县', 'DC 充电头数量', '白天价格', '夜间价格', 'AC 充电头数量', '白天价格', '夜间价格', '提交人姓名', '电话 / 邮箱（用于反馈）', '补充说明'],
        placeholders: ['例如：PTT EV Station Sathorn, WEH Charging Asok', '例如：某大楼 B1 层、某路、某区...', '例如：曼谷', '例如：Watthana, Bang Rak', '例如：2', '例如：7.50', '例如：5.50', '例如：4', '例如：7.50', '例如：5.50', '营业时间、费用、需要使用的 App 或其他有用信息...'],
        dc: '⚡ 有 DC 快充头',
        ac: '🔌 有 AC 充电头',
        submit: '提交 ✓',
        thanksTitle: '感谢你帮助完善系统！',
        thanksBody: '你的信息已提交给团队审核，我们会尽快加入系统。',
        another: '继续提交信息',
        errors: { station: '请填写站点名称', province: '请填写府/省', generic: '提交失败，请再试一次。' },
      },
    },
  };

  const LEGAL = {
    privacy: {
      en: {
        title: 'Privacy Policy (PDPA) — EV Stations Thailand',
        eyebrow: 'PDPA',
        h1: 'Privacy Policy',
        updated: 'Effective: 16 June 2025 · Last updated: 16 June 2025',
        toc: ['1. Introduction', '2. Data controller', '3. Data we collect', '4. Purpose', '5. Disclosure', '6. Local Storage', '7. Retention', '8. Your rights', '9. Security', '10. Changes', '11. Contact'],
        sections: [
          ['Introduction', ['EV Stations Thailand values user privacy. This policy explains how the website collects, uses, and protects personal data under Thailand PDPA.', 'This is a static EV charging station information platform. Most user data is stored only in the browser Local Storage on your own device.']],
          ['Personal data controller', ['Controller: EV Stations Thailand. Type: static EV charging station information website without a central user database. Contact email: {{email}}.']],
          ['Data we collect', ['Reviews may include your display name, rating, comment, station ID, and submission time.', 'Interest and station-information forms may include name, phone, email, province, station information, and optional notes.', 'The website may store preferences such as language, theme, local admin settings, local reviews, and local traffic counters in your browser.']],
          ['Purpose and lawful basis', ['We use data to display reviews, receive station updates, manage local preferences, improve usability, and respond to user contact. Processing is based on user consent, legitimate interest, and actions requested by the user.']],
          ['Disclosure and transfer', ['This local static copy does not send form submissions or reviews to a central server by itself. External links such as Google Maps open third-party services governed by their own policies.']],
          ['Local Storage', ['Local Storage keeps settings and local submissions on your device. Clearing browser site data will remove them. Data stored this way is not automatically shared with other users or devices.']],
          ['Retention', ['Browser-stored data remains until you delete it, clear site data, change browser/device, or use an available delete/reset control.']],
          ['Your rights', ['You may request access, correction, deletion, restriction, objection, portability, or withdrawal of consent where applicable. For locally stored data, you can also clear it directly in your browser.']],
          ['Security', ['We use static-site practices and browser-side storage. You should protect your own device and avoid entering sensitive information into public or shared browsers.']],
          ['Policy changes', ['We may update this policy from time to time. Changes are effective when published on this page.']],
          ['Contact', ['For privacy questions or data-rights requests, contact us at {{email}}. We aim to respond within 3-5 business days.']],
        ],
      },
      zh: {
        title: '隐私政策（PDPA）— EV Stations Thailand',
        eyebrow: 'PDPA',
        h1: '隐私政策',
        updated: '生效日期：2025 年 6 月 16 日 · 最近更新：2025 年 6 月 16 日',
        toc: ['1. 简介', '2. 数据控制者', '3. 我们收集的数据', '4. 使用目的', '5. 披露与转移', '6. Local Storage', '7. 保存期限', '8. 你的权利', '9. 数据安全', '10. 政策变更', '11. 联系方式'],
        sections: [
          ['简介', ['EV Stations Thailand 重视每位用户的隐私。本政策根据泰国个人资料保护法（PDPA）说明网站如何收集、使用和保护个人数据。', '本网站是泰国电动车充电站信息平台。本地静态版本没有中央用户数据库，大多数用户数据仅保存在你自己设备的浏览器 Local Storage 中。']],
          ['个人数据控制者', ['数据控制者：EV Stations Thailand。类型：静态充电站信息网站，无中央用户数据库。联系邮箱：{{email}}。']],
          ['我们收集的数据', ['评价可能包含显示名称、评分、评论内容、站点 ID 和提交时间。', '合作意向和站点信息表单可能包含姓名、电话、邮箱、府/省、站点资料和补充说明。', '网站可能在浏览器中保存语言、主题、本地管理设置、本地评价和本地访问计数等偏好数据。']],
          ['使用目的和法律基础', ['我们使用数据来展示评价、接收站点更新、管理本地偏好、改善使用体验，以及回应用户联系。处理基础包括用户同意、合法利益和用户主动请求的操作。']],
          ['披露与转移', ['本地静态副本本身不会把表单或评价提交到中央服务器。Google Maps 等外部链接会打开第三方服务，并适用其各自的隐私政策。']],
          ['Local Storage', ['Local Storage 会把设置和本地提交内容保存在你的设备上。清除浏览器网站数据会删除这些内容。这类数据不会自动同步到其他用户或设备。']],
          ['保存期限', ['浏览器中的数据会保留到你删除、清除网站数据、更换浏览器/设备，或使用页面中的删除/重置功能为止。']],
          ['你的权利', ['在适用法律下，你可以请求访问、更正、删除、限制处理、反对处理、数据可携带或撤回同意。对于本地保存的数据，你也可以直接在浏览器中清除。']],
          ['数据安全', ['我们采用静态网站和浏览器端存储方式。请保护好自己的设备，避免在公共或共享浏览器中输入敏感信息。']],
          ['政策变更', ['我们可能不时更新本政策。变更发布到本页面后立即生效。']],
          ['联系方式', ['如有隐私问题或数据权利请求，请通过 {{email}} 联系我们。我们会尽量在 3-5 个工作日内回复。']],
        ],
      },
    },
    terms: {
      en: {
        title: 'Terms of Service — EV Stations Thailand',
        eyebrow: 'Terms of Service',
        h1: 'Terms of Service',
        updated: 'Effective: 16 June 2025 · Last updated: 16 June 2025',
        toc: ['1. Acceptance', '2. Service', '3. Data accuracy', '4. User content', '5. Prohibited use', '6. Intellectual property', '7. Limitation of liability', '8. Governing law', '9. Changes', '10. Contact'],
        sections: [
          ['Acceptance of terms', ['By accessing or using EV Stations Thailand, you acknowledge that you have read, understood, and agreed to these terms. If you do not agree, please stop using the website.']],
          ['Service and scope', ['EV Stations Thailand provides a free platform for browsing EV charging station information in Thailand, including map search, filtering, station details, reviews, and submission forms. We may modify, suspend, or discontinue parts of the service.']],
          ['Station data accuracy', ['We try to keep charging station information accurate and current, but we do not guarantee completeness, accuracy, availability, pricing, operating hours, or real-time charger status. Always verify critical details before travel.']],
          ['User-submitted content', ['Users may submit reviews, station updates, or interest forms. You are responsible for ensuring submitted content is accurate, lawful, and does not infringe rights or contain harmful material.']],
          ['Prohibited use', ['Do not misuse the website, attempt unauthorized access, submit false or harmful content, scrape excessively, interfere with service operation, or violate applicable laws.']],
          ['Intellectual property', ['Website design, code, text, and compilation are protected by applicable intellectual-property laws. Third-party names, logos, maps, and data remain the property of their respective owners.']],
          ['Limitation of liability', ['The website is provided as-is. We are not liable for losses caused by inaccurate station data, unavailable chargers, third-party services, device/browser issues, or user-submitted content.']],
          ['Governing law and jurisdiction', ['These terms are governed by the laws of Thailand, unless another mandatory law applies.']],
          ['Changes to terms', ['We may update these terms at any time. Continued use after changes means you accept the updated terms.']],
          ['Contact', ['For questions about these terms, contact us at {{email}}. For privacy matters, please see the Privacy Policy.']],
        ],
      },
      zh: {
        title: '服务条款 — EV Stations Thailand',
        eyebrow: '服务条款',
        h1: '服务条款',
        updated: '生效日期：2025 年 6 月 16 日 · 最近更新：2025 年 6 月 16 日',
        toc: ['1. 接受条款', '2. 服务范围', '3. 数据准确性', '4. 用户内容', '5. 禁止行为', '6. 知识产权', '7. 责任限制', '8. 适用法律', '9. 条款变更', '10. 联系方式'],
        sections: [
          ['接受条款', ['访问或使用 EV Stations Thailand 即表示你已阅读、理解并同意本服务条款。如不同意，请停止使用本网站。']],
          ['服务与范围', ['EV Stations Thailand 免费提供泰国 EV 充电站信息浏览服务，包括地图搜索、筛选、站点详情、评价以及信息提交表单。我们可以修改、暂停或终止部分服务。']],
          ['站点数据准确性', ['我们会尽力保持充电站信息准确和更新，但不保证所有数据完整、准确、实时可用，也不保证价格、营业时间或充电头状态。出行前请自行核实重要信息。']],
          ['用户提交内容', ['用户可提交评价、站点更新或合作意向。你需要确保提交内容准确、合法，不侵犯他人权利，也不包含有害内容。']],
          ['禁止行为', ['不得滥用网站、尝试未授权访问、提交虚假或有害内容、过度抓取、干扰服务运行，或违反适用法律。']],
          ['知识产权', ['网站设计、代码、文字和数据汇编受相关知识产权法律保护。第三方名称、Logo、地图和数据归其各自权利人所有。']],
          ['责任限制', ['本网站按现状提供。因站点数据不准确、充电设备不可用、第三方服务、设备/浏览器问题或用户提交内容造成的损失，我们不承担责任。']],
          ['适用法律和管辖', ['本条款受泰国法律管辖，除非强制性法律另有规定。']],
          ['条款变更', ['我们可随时更新本条款。条款更新后继续使用网站，即表示你接受更新后的条款。']],
          ['联系方式', ['如对本条款有疑问，请通过 {{email}} 联系我们。隐私相关事项请参阅隐私政策。']],
        ],
      },
    },
  };

  function lang() { return (window.EVi18n && EVi18n.getLang()) || 'th'; }
  function dict(page) { return (PAGES[page] && PAGES[page][lang()]) || null; }
  function common() { return COMMON[lang()] || COMMON.th; }
  function q(selector) { return document.querySelector(selector); }
  function qa(selector) { return Array.from(document.querySelectorAll(selector)); }
  function text(selector, value) { const el = q(selector); if (el && value !== undefined) el.textContent = value; }
  function html(selector, value) { const el = q(selector); if (el && value !== undefined) el.innerHTML = value; }
  function placeholder(selector, value) { const el = q(selector); if (el && value !== undefined) el.placeholder = value; }

  function applyCommon() {
    text('.back', common().back);
    const footerLinks = qa('.site-footer a');
    if (footerLinks[0]) footerLinks[0].textContent = common().privacy;
    if (footerLinks[1]) footerLinks[1].textContent = common().terms;
  }

  function applyAbout() {
    applyCommon();
    const d = dict('about');
    if (!d) return;
    document.title = d.title;
    text('.about-hero .hero-eyebrow', d.eyebrow);
    text('#aboutTitle', d.heroTitle);
    text('#aboutTagline', d.tagline);
    qa('.stat-label').forEach((el, i) => { if (d.stats[i]) el.textContent = d.stats[i]; });
    text('#missionSection h2', d.missionTitle);
    text('#missionText', d.mission);
    const sections = qa('.about-section h2');
    if (sections[1]) sections[1].textContent = d.providersTitle;
    const providersBody = q('.about-section:nth-of-type(2) p');
    if (providersBody) providersBody.textContent = d.providersBody;
    qa('.provider-card .p-label').forEach(el => { el.textContent = d.stationLabel; });
    text('#contactSection h2', d.contactTitle);
    text('.about-cta h2', d.ctaTitle);
    text('.about-cta p', d.ctaBody);
    const cta = qa('.about-cta a');
    if (cta[0]) cta[0].textContent = d.addInfo;
    if (cta[1]) cta[1].textContent = d.interested;
  }

  function applyInterested() {
    applyCommon();
    const d = dict('interested');
    if (!d) return;
    document.title = d.title;
    text('.interested-hero h1', d.heroTitle);
    text('.interested-hero p', d.heroBody);
    qa('.benefit-card').forEach((card, i) => {
      if (!d.benefits[i]) return;
      const title = card.querySelector('.title');
      const desc = card.querySelector('.desc');
      if (title) title.textContent = d.benefits[i][0];
      if (desc) desc.textContent = d.benefits[i][1];
    });
    text('#formCard > h2', d.formTitle);
    text('#formCard > .subtitle', d.subtitle);
    html('#formCard > .required-note', d.required);
    qa('#interestedForm .label').forEach((el, i) => { if (d.labels[i]) el.innerHTML = d.labels[i]; });
    placeholder('#fprovince', d.provincePlaceholder);
    qa('input[name="interestType"]').forEach((el, i) => { if (d.radios[i]) el.value = d.radios[i].replace(/^[^ ]+ /, ''); });
    qa('.radio-option span').forEach((el, i) => { if (d.radios[i]) el.textContent = d.radios[i]; });
    placeholder('#fdetails', d.detailsPlaceholder);
    text('#interestedForm button[type="submit"]', d.submit);
    text('#thankYou h2', d.thanksTitle);
    text('#thankYou p', d.thanksBody);
    text('#thankYou a', common().map);
  }

  function applyAddInfo() {
    applyCommon();
    const d = dict('addInfo');
    if (!d) return;
    document.title = d.title;
    text('.add-hero h1', d.heroTitle);
    text('.add-hero p', d.heroBody);
    text('#formCard > h2', d.formTitle);
    text('#formCard > .subtitle', d.subtitle);
    html('#formCard > .required-note', d.required);
    qa('#addInfoForm .section-label').forEach((el, i) => { if (d.sectionLabels[i]) el.textContent = d.sectionLabels[i]; });
    qa('.type-card .type-name').forEach((el, i) => { if (d.typeNames[i]) el.textContent = d.typeNames[i]; });
    qa('.type-card .type-desc').forEach((el, i) => { if (d.typeDescs[i]) el.textContent = d.typeDescs[i]; });
    qa('#addInfoForm .label').forEach((el, i) => { if (d.labels[i]) el.innerHTML = d.labels[i]; });
    const ph = ['#fStationName', '#fAddress', '#fProvince', '#fDistrict', '#fDcHeads', '#fDcDayPrice', '#fDcNightPrice', '#fAcHeads', '#fAcDayPrice', '#fAcNightPrice', '#fNotes'];
    ph.forEach((selector, i) => placeholder(selector, d.placeholders[i]));
    const checkbox = qa('.checkbox-row span');
    if (checkbox[0]) checkbox[0].textContent = d.dc;
    if (checkbox[1]) checkbox[1].textContent = d.ac;
    text('#addInfoForm button[type="submit"]', d.submit);
    text('#thankYou h2', d.thanksTitle);
    text('#thankYou p', d.thanksBody);
    text('#submitAnotherBtn', d.another);
    const thanksLinks = qa('#thankYou a');
    if (thanksLinks[0]) thanksLinks[0].textContent = common().map;
  }

  function renderLegal(kind) {
    const d = LEGAL[kind] && LEGAL[kind][lang()];
    applyCommon();
    updateLegalFooter(kind);
    if (!d) return;
    document.title = d.title;
    text('.legal-hero .eyebrow', d.eyebrow);
    text('.legal-hero h1', d.h1);
    text('.legal-hero .updated', d.updated);
    const toc = q('.legal-toc');
    if (toc) {
      const prefix = kind === 'privacy' ? 's' : 't';
      toc.setAttribute('aria-label', lang() === 'zh' ? '目录' : 'Table of contents');
      toc.innerHTML = d.toc.map((item, i) => `<a href="#${prefix}${i + 1}">${item}</a>`).join('');
    }
    const body = q('.legal-body');
    if (body) {
      const email = legalEmailHtml();
      body.innerHTML = d.sections.map((section, i) => `
        <div class="legal-section" id="${kind === 'privacy' ? 's' : 't'}${i + 1}">
          <div class="legal-section-head">
            <span class="legal-section-num">${String(i + 1).padStart(2, '0')}</span>
            <h2>${section[0]}</h2>
          </div>
          ${section[1].map(p => `<p>${p.replace(/\{\{email\}\}/g, email)}</p>`).join('')}
        </div>`).join('');
    }
  }

  function legalEmailHtml() {
    const aboutData = (window.EVApp && EVApp.getAbout && EVApp.getAbout()) || {};
    const email = aboutData.email || 'phuketthongsom@gmail.com';
    const safe = window.EVApp && EVApp.escapeHtml ? EVApp.escapeHtml(email) : email;
    return `<a href="mailto:${safe}" style="color:var(--accent);">${safe}</a>`;
  }

  function updateLegalFooter(kind) {
    const labels = {
      th: { map: '🗺️ แผนที่', about: 'เกี่ยวกับเรา', privacy: 'นโยบายความเป็นส่วนตัว', terms: 'ข้อกำหนดการใช้งาน' },
      en: { map: '🗺️ Map', about: 'About us', privacy: 'Privacy Policy', terms: 'Terms of Service' },
      zh: { map: '🗺️ 地图', about: '关于我们', privacy: '隐私政策', terms: '服务条款' },
    }[lang()] || {};
    qa('.legal-page-footer a').forEach(a => {
      const href = a.getAttribute('href') || '';
      if (href.includes('index')) a.textContent = labels.map;
      if (href.includes('about')) a.textContent = labels.about;
      if (href.includes('privacy')) a.textContent = labels.privacy;
      if (href.includes('terms')) a.textContent = labels.terms;
    });
  }

  function apply(page) {
    if (page === 'about') applyAbout();
    if (page === 'interested') applyInterested();
    if (page === 'addInfo') applyAddInfo();
    if (page === 'privacy') renderLegal('privacy');
    if (page === 'terms') renderLegal('terms');
  }

  function t(page, key) {
    const d = dict(page);
    return key.split('.').reduce((obj, part) => obj && obj[part], d) || key;
  }

  return { apply, t };
})();
