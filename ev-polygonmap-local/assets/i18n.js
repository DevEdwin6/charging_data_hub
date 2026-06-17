// i18n module — TH (default), EN, and ZH
window.EVi18n = (function () {
  const KEY_LANG   = 'evmap.lang';
  const KEY_CUSTOM = 'evmap.i18n.custom.'; // + lang code
  const LANGS = [
    { code: 'th', label: 'Thai' },
    { code: 'en', label: 'English' },
    { code: 'zh', label: '中文' },
  ];

  // ─── String tables ───────────────────────────────────────────────
  const STRINGS = {
    th: {
      // Navigation
      nav_home:        'หน้าหลัก',
      nav_about:       'เกี่ยวกับเรา',
      nav_interested:  'สนใจทำสถานี',
      nav_addInfo:     'เพิ่มข้อมูล',
      nav_blog:        'บล็อก',
      nav_back:        '← กลับ',

      // Header
      stats_stations:  '{n} สถานี',

      // Search
      search_placeholder: 'ค้นหาสถานี จังหวัด อำเภอ…',
      btn_nearMe:         '📍 ใกล้ฉัน',
      btn_fitToFiltered:  'ปรับมุมมองตามสถานีที่กรอง',
      btn_myLocation:     'ตำแหน่งของฉัน',

      // Filters
      filter_provider: 'ผู้ให้บริการ',
      filter_type:     'ประเภท',
      filter_minHeads: 'หัวชาร์จขั้นต่ำ',
      filter_any:      'ทั้งหมด',
      filter_reset:    '↺ รีเซ็ต',

      // Sort
      sort_prefix:   'เรียง: ',
      sort_default:  'ค่าเริ่มต้น',
      sort_distance: 'ระยะทาง',
      sort_heads:    'หัวชาร์จมากสุด',

      // List view
      list_head_stations: 'สถานี',
      list_head_inView:   '{n} รายการ',
      list_empty_title:   'ไม่มีสถานีในพื้นที่นี้',
      list_empty_body:    'เลื่อนหรือซูมออกเพื่อหาสถานี หรือล้างตัวกรองของคุณ',
      list_showing_cap:   'แสดง {cap} จาก {total} สถานี ซูมเข้าเพื่อลดผลลัพธ์',
      btn_directions:     '🧭 นำทาง',
      btn_details:        '📄 รายละเอียด',
      toggle_list:        '📋 รายการ',
      toggle_map:         '🗺 แผนที่',
      sidebar_collapse:   'ซ่อนแถบข้าง',
      sidebar_expand:     'แสดงแถบข้าง',

      // Toast
      toast_locating:        'กำลังค้นหาตำแหน่ง…',
      toast_nearYou:         'แสดงสถานีใกล้คุณ',
      toast_nearMeFirst:     "กดปุ่ม 'ใกล้ฉัน' ก่อนเพื่อเรียงตามระยะทาง",
      toast_geoNotSupported: 'เบราว์เซอร์นี้ไม่รองรับการระบุตำแหน่ง',
      toast_geoError:        'ไม่สามารถรับตำแหน่งของคุณได้: {error}',

      // Station page
      station_not_found:          'ไม่พบสถานี',
      station_back:               '← กลับไปแผนที่',
      station_chargers:           'ตัวชาร์จ ({n})',
      station_charger_label:      'ตัวชาร์จ',
      station_head_label:         'หัวชาร์จ',
      station_get_directions:     '🧭 นำทาง',
      station_copy_link:          '🔗 คัดลอกลิงก์',
      station_share:              '📤 แชร์',
      station_charging_capacity:  'ความจุการชาร์จ',
      station_dc_fast:            'DC เร็ว',
      station_ac:                 'AC',
      station_total_heads:        'หัวชาร์จทั้งหมด',
      station_reviews:            'รีวิว',
      station_write_review:       'เขียนรีวิว',
      station_your_name:          'ชื่อของคุณ',
      station_name_placeholder:   'เช่น สมชาย ก.',
      station_rating:             'คะแนน',
      station_experience:         'ประสบการณ์ของคุณ',
      station_exp_placeholder:    'ความเร็วชาร์จ ความน่าเชื่อถือ สิ่งอำนวยความสะดวก ที่จอดรถ…',
      station_submit:             'ส่งรีวิว',
      station_approval_notice:    'รีวิวจะแสดงหลังจากผ่านการอนุมัติ',
      station_no_reviews_title:   'ยังไม่มีรีวิว',
      station_no_reviews_body:    'เป็นคนแรกที่แบ่งปันประสบการณ์การชาร์จของคุณ',
      station_based_on:           'จากรีวิว {n} รายการ',
      station_review_submitted:   'ส่งรีวิวแล้ว — รอการอนุมัติจากผู้ดูแล',
      station_link_copied:        'คัดลอกลิงก์แล้ว',
      station_please_rate:        'กรุณาเลือกคะแนน (1–5 ดาว)',
      station_unnamed_charger:    'ตัวชาร์จไม่ระบุชื่อ',
      station_you_are_here:       'คุณอยู่ที่นี่',
      station_gun_label:          'หัวชาร์จ {n}',
      station_day_price:          'กลางวัน',
      station_night_price:        'กลางคืน',
      station_price_missing:      'ยังไม่มีราคา',
      station_price_unit_kwh:     'kWh',
      station_kw_label:           '{kw} kW',

      // Time
      time_just_now: 'เมื่อกี้',
      time_m_ago:    '{n} นาทีที่แล้ว',
      time_h_ago:    '{n} ชั่วโมงที่แล้ว',
      time_d_ago:    '{n} วันที่แล้ว',

      // Admin – login
      admin_login_title:    '🔒 เข้าสู่ระบบผู้ดูแล',
      admin_login_subtitle: 'กรอกรหัสผ่านเพื่อจัดการระบบ',
      admin_password:       'รหัสผ่าน',
      admin_sign_in:        'เข้าสู่ระบบ',
      admin_default_hint:   '💡 ครั้งแรก? รหัสผ่านเริ่มต้นคือ <code>admin</code> เปลี่ยนรหัสผ่านหลังจากเข้าสู่ระบบ',

      // Admin – tabs
      admin_tab_dashboard: '📊 แดชบอร์ด',
      admin_tab_pending:   '⏳ รีวิวรอดำเนินการ',
      admin_tab_approved:  '✅ รีวิวที่อนุมัติแล้ว',
      admin_tab_brand:     '🎨 แบรนด์ & โลโก้',
      admin_tab_settings:  '⚙️ การตั้งค่า',
      admin_tab_language:  '🌐 ภาษา',

      // Admin – dashboard
      admin_total_stations:   'สถานีทั้งหมด',
      admin_pending_label:    'รีวิวรอดำเนินการ',
      admin_approved_label:   'รีวิวที่อนุมัติแล้ว',
      admin_avg_rating:       'คะแนนเฉลี่ย',
      admin_recent_activity:  'กิจกรรมล่าสุด',
      admin_no_activity:      'ยังไม่มีกิจกรรม',

      // Admin – reviews
      admin_all_clear:    'ทุกอย่างเรียบร้อย!',
      admin_no_pending:   'ไม่มีรีวิวรอการอนุมัติ',
      admin_n_pending:    '{n} รอดำเนินการ',
      admin_approve:      '✓ อนุมัติ',
      admin_reject:       '✕ ปฏิเสธ',
      admin_view_page:    'ดูหน้า →',
      admin_no_approved:  'ยังไม่มีรีวิวที่อนุมัติ',
      admin_n_approved:   '{n} อนุมัติแล้ว',
      admin_delete:       '🗑 ลบ',
      badge_pending:      'รอดำเนินการ',
      badge_approved:     'อนุมัติแล้ว',

      // Admin – brand
      admin_logo_section:         'โลโก้',
      admin_no_logo:              'ยังไม่ได้อัปโหลดโลโก้',
      admin_upload_logo:          '⬆️ อัปโหลดโลโก้',
      admin_remove:               'ลบออก',
      admin_logo_help:            'PNG, JPG, SVG หรือ WebP แนะนำขนาดน้อยกว่า 200 KB โลโก้จะถูกเก็บในเบราว์เซอร์นี้เท่านั้น — ไม่แสดงในเบราว์เซอร์อื่น พื้นที่ที่ใช้:',
      admin_header_preview:       'ตัวอย่างหัวเว็บ',
      admin_provider_logos:       'โลโก้ผู้ให้บริการ',
      admin_provider_logos_help:  'แต่ละแบรนด์สามารถมีโลโก้แสดงในชิปตัวกรองและป้ายสถานี',
      admin_no_logo_short:        'ยังไม่มีโลโก้',
      admin_upload:               '⬆️ อัปโหลด',
      admin_brand_name:           'ชื่อแบรนด์',
      admin_save_brand:           'บันทึกชื่อแบรนด์',

      // Admin – settings
      admin_change_password:  'เปลี่ยนรหัสผ่าน',
      admin_current_password: 'รหัสผ่านปัจจุบัน',
      admin_new_password:     'รหัสผ่านใหม่',
      admin_update_password:  'อัปเดตรหัสผ่าน',
      admin_data_management:  'การจัดการข้อมูล',
      admin_data_help:        'รีวิวและแบรนด์จะถูกเก็บใน localStorage ของเบราว์เซอร์',
      admin_export_data:      '📥 ส่งออกข้อมูลทั้งหมด',
      admin_clear_reviews:    '🗑 ลบรีวิวทั้งหมด',

      // Admin – language editor
      admin_lang_title:    'ตัวแก้ไขภาษา',
      admin_lang_subtitle: 'แก้ไขคำแปลสำหรับภาษาไทยและภาษาอังกฤษ การเปลี่ยนแปลงจะถูกบันทึกในเบราว์เซอร์นี้',
      admin_lang_save:     'บันทึกคำแปล',
      admin_lang_reset:    'รีเซ็ตเป็นค่าเริ่มต้น',
      admin_lang_export:   '📥 ส่งออก JSON',
      admin_lang_import:   '📤 นำเข้า JSON',
      admin_lang_col_key:  'หัวข้อ',
      admin_lang_col_th:   'ภาษาไทย',
      admin_lang_col_en:   'ภาษาอังกฤษ',
      admin_lang_col_zh:   'ภาษาจีน',

      // Admin – toast messages
      admin_toast_sign_out:      'ออกจากระบบแล้ว',
      admin_toast_welcome:       'ยินดีต้อนรับกลับ',
      admin_toast_wrong_pw:      'รหัสผ่านไม่ถูกต้อง',
      admin_toast_pw_updated:    'อัปเดตรหัสผ่านแล้ว',
      admin_toast_cur_pw_wrong:  'รหัสผ่านปัจจุบันไม่ถูกต้อง',
      admin_toast_longer_pw:     'กรุณาใช้รหัสผ่านที่ยาวกว่านี้',
      admin_toast_exported:      'ส่งออกข้อมูลแล้ว',
      admin_toast_all_deleted:   'ลบรีวิวทั้งหมดแล้ว',
      admin_toast_approved:      'อนุมัติรีวิวแล้ว',
      admin_toast_rejected:      'ปฏิเสธรีวิวแล้ว',
      admin_toast_deleted:       'ลบรีวิวแล้ว',
      admin_toast_logo_saved:    'บันทึกโลโก้แล้ว ({kb} KB)',
      admin_toast_logo_removed:  'ลบโลโก้แล้ว',
      admin_toast_brand_saved:   'บันทึกชื่อแบรนด์แล้ว',
      admin_toast_save_failed:   'บันทึกไม่สำเร็จ — ไฟล์ใหญ่เกินไป ลองไฟล์ที่เล็กกว่า (< 200 KB)',
      admin_toast_prov_saved:    'บันทึกโลโก้ {p} แล้ว ({kb} KB)',
      admin_toast_trans_saved:   'บันทึกคำแปลแล้ว',
      admin_toast_trans_reset:   'รีเซ็ตคำแปลเป็นค่าเริ่มต้นแล้ว',
      admin_toast_trans_imported:'นำเข้าคำแปลแล้ว',

      // Confirm dialogs
      confirm_delete_review:    'ลบรีวิวที่อนุมัติแล้วนี้?',
      confirm_clear_all:        'ลบรีวิวทั้งหมด (ทั้งรอดำเนินการและอนุมัติ)? ไม่สามารถเรียกคืนได้',
      confirm_remove_logo:      'ลบโลโก้ปัจจุบัน?',
      confirm_remove_prov_logo: 'ลบโลโก้ {p}?',
      confirm_large_image:      'ไฟล์นี้มีขนาด {kb} KB — ไฟล์ขนาดใหญ่อาจเกินขีดจำกัด storage ดำเนินการต่อ?',
      cookie_text:              'เว็บไซต์นี้ใช้ Local Storage เพื่อจดจำการตั้งค่าและเก็บรีวิวบนอุปกรณ์ของคุณ อ่าน <a href="privacy.html">นโยบายความเป็นส่วนตัว</a> และ <a href="terms.html">ข้อกำหนดการใช้งาน</a>',
      cookie_decline:           'ปฏิเสธ',
      cookie_accept:            'ยอมรับ',

      // Language toggle button text (shows what you'd switch TO)
      lang_btn: 'EN',
    },

    en: {
      nav_home:        'Home',
      nav_about:       'About us',
      nav_interested:  'Build a station',
      nav_addInfo:     'Add info',
      nav_blog:        'Blog',
      nav_back:        '← Back',

      stats_stations:  '{n} stations',

      search_placeholder: 'Search station, province, district…',
      btn_nearMe:         '📍 Near me',
      btn_fitToFiltered:  'Fit to filtered stations',
      btn_myLocation:     'My location',

      filter_provider: 'Provider',
      filter_type:     'Type',
      filter_minHeads: 'Min. Heads',
      filter_any:      'Any',
      filter_reset:    '↺ Reset',

      sort_prefix:   'Sort: ',
      sort_default:  'Default',
      sort_distance: 'Distance',
      sort_heads:    'Most heads',

      list_head_stations: 'Stations',
      list_head_inView:   '{n} in view',
      list_empty_title:   'No stations in view',
      list_empty_body:    'Pan or zoom out to find stations, or clear your filters.',
      list_showing_cap:   'Showing {cap} of {total} stations in view. Zoom in to narrow results.',
      btn_directions:     '🧭 Directions',
      btn_details:        '📄 Details',
      toggle_list:        '📋 List',
      toggle_map:         '🗺 Map',
      sidebar_collapse:   'Collapse sidebar',
      sidebar_expand:     'Expand sidebar',

      toast_locating:        'Locating…',
      toast_nearYou:         'Showing stations near you',
      toast_nearMeFirst:     "Tap 'Near me' first to enable distance sort.",
      toast_geoNotSupported: 'Geolocation not supported.',
      toast_geoError:        'Could not get your location: {error}',

      station_not_found:         'Station not found',
      station_back:              '← Back to map',
      station_chargers:          'Chargers ({n})',
      station_charger_label:     'chargers',
      station_head_label:        'heads',
      station_get_directions:    '🧭 Get Directions',
      station_copy_link:         '🔗 Copy Link',
      station_share:             '📤 Share',
      station_charging_capacity: 'Charging Capacity',
      station_dc_fast:           'DC Fast',
      station_ac:                'AC',
      station_total_heads:       'Total Heads',
      station_reviews:           'Reviews',
      station_write_review:      'Write a review',
      station_your_name:         'Your name',
      station_name_placeholder:  'e.g. Pream T.',
      station_rating:            'Rating',
      station_experience:        'Your experience',
      station_exp_placeholder:   'Charging speed, reliability, amenities, parking, anything helpful…',
      station_submit:            'Submit Review',
      station_approval_notice:   'Reviews appear after admin approval.',
      station_no_reviews_title:  'No reviews yet',
      station_no_reviews_body:   'Be the first to share your charging experience.',
      station_based_on:          'Based on {n} review{s}',
      station_review_submitted:  'Review submitted — awaiting admin approval',
      station_link_copied:       'Link copied to clipboard',
      station_please_rate:       'Please pick a rating (1–5 stars)',
      station_unnamed_charger:   'Unnamed charger',
      station_you_are_here:      'You are here',
      station_gun_label:         'Gun {n}',
      station_day_price:         'Day',
      station_night_price:       'Night',
      station_price_missing:     'Price not provided',
      station_price_unit_kwh:    'kWh',
      station_kw_label:          '{kw} kW',

      time_just_now: 'just now',
      time_m_ago:    '{n}m ago',
      time_h_ago:    '{n}h ago',
      time_d_ago:    '{n}d ago',

      admin_login_title:    '🔒 Admin Login',
      admin_login_subtitle: 'Enter the admin password to manage the site.',
      admin_password:       'Password',
      admin_sign_in:        'Sign In',
      admin_default_hint:   '💡 First time? The default password is <code>admin</code>. Change it once you log in.',

      admin_tab_dashboard: '📊 Dashboard',
      admin_tab_pending:   '⏳ Pending Reviews',
      admin_tab_approved:  '✅ Approved Reviews',
      admin_tab_brand:     '🎨 Brand & Logo',
      admin_tab_settings:  '⚙️ Settings',
      admin_tab_language:  '🌐 Language',

      admin_total_stations:   'Total Stations',
      admin_pending_label:    'Pending Reviews',
      admin_approved_label:   'Approved Reviews',
      admin_avg_rating:       'Avg Rating',
      admin_recent_activity:  'Recent activity',
      admin_no_activity:      'No activity yet.',

      admin_all_clear:    'All clear!',
      admin_no_pending:   'No reviews waiting for approval.',
      admin_n_pending:    '{n} pending',
      admin_approve:      '✓ Approve',
      admin_reject:       '✕ Reject',
      admin_view_page:    'View page →',
      admin_no_approved:  'No approved reviews yet.',
      admin_n_approved:   '{n} approved',
      admin_delete:       '🗑 Delete',
      badge_pending:      'Pending',
      badge_approved:     'Approved',

      admin_logo_section:         'Logo',
      admin_no_logo:              'No logo uploaded',
      admin_upload_logo:          '⬆️ Upload Logo',
      admin_remove:               'Remove',
      admin_logo_help:            'PNG, JPG, SVG or WebP. Recommended under 200 KB. Logos are stored in this browser only — they won\'t appear in other browsers or after clearing site data. Storage used:',
      admin_header_preview:       'Header preview',
      admin_provider_logos:       'Provider Logos',
      admin_provider_logos_help:  'Each brand can have its own logo shown in filter chips and station badges.',
      admin_no_logo_short:        'No logo',
      admin_upload:               '⬆️ Upload',
      admin_brand_name:           'Brand Name',
      admin_save_brand:           'Save Brand Name',

      admin_change_password:  'Change Password',
      admin_current_password: 'Current password',
      admin_new_password:     'New password',
      admin_update_password:  'Update Password',
      admin_data_management:  'Data Management',
      admin_data_help:        "Reviews and branding are stored in your browser's localStorage.",
      admin_export_data:      '📥 Export All Data',
      admin_clear_reviews:    '🗑 Clear All Reviews',

      admin_lang_title:    'Language Editor',
      admin_lang_subtitle: 'Edit translations for Thai and English. Changes are saved in this browser.',
      admin_lang_save:     'Save Translations',
      admin_lang_reset:    'Reset to Defaults',
      admin_lang_export:   '📥 Export JSON',
      admin_lang_import:   '📤 Import JSON',
      admin_lang_col_key:  'Key',
      admin_lang_col_th:   'Thai',
      admin_lang_col_en:   'English',
      admin_lang_col_zh:   'Chinese',

      admin_toast_sign_out:      'Signed out',
      admin_toast_welcome:       'Welcome back',
      admin_toast_wrong_pw:      'Wrong password',
      admin_toast_pw_updated:    'Password updated',
      admin_toast_cur_pw_wrong:  'Current password is wrong',
      admin_toast_longer_pw:     'Pick a longer password',
      admin_toast_exported:      'Data exported',
      admin_toast_all_deleted:   'All reviews deleted',
      admin_toast_approved:      'Review approved',
      admin_toast_rejected:      'Review rejected',
      admin_toast_deleted:       'Review deleted',
      admin_toast_logo_saved:    'Logo saved ({kb} KB)',
      admin_toast_logo_removed:  'Logo removed',
      admin_toast_brand_saved:   'Brand name saved',
      admin_toast_save_failed:   'Save failed — image too large for browser storage. Try a smaller file (< 200 KB).',
      admin_toast_prov_saved:    '{p} logo saved ({kb} KB)',
      admin_toast_trans_saved:   'Translations saved',
      admin_toast_trans_reset:   'Translations reset to defaults',
      admin_toast_trans_imported:'Translations imported',

      confirm_delete_review:    'Delete this approved review?',
      confirm_clear_all:        'Delete ALL reviews (both pending and approved)? This cannot be undone.',
      confirm_remove_logo:      'Remove the current logo?',
      confirm_remove_prov_logo: 'Remove {p} logo?',
      confirm_large_image:      'This image is {kb} KB — large images may hit browser storage limits. Continue?',
      cookie_text:              'This site uses Local Storage to remember settings and store reviews on your device. Read the <a href="privacy.html">Privacy Policy</a> and <a href="terms.html">Terms of Service</a>.',
      cookie_decline:           'Decline',
      cookie_accept:            'Accept',

      lang_btn: '中文',
    },

    zh: {
      nav_home:        '首页',
      nav_about:       '关于我们',
      nav_interested:  '建设充电站',
      nav_addInfo:     '补充信息',
      nav_blog:        '博客',
      nav_back:        '← 返回',

      stats_stations:  '{n} 个站点',

      search_placeholder: '搜索站点、省份、地区…',
      btn_nearMe:         '📍 附近',
      btn_fitToFiltered:  '缩放到筛选结果',
      btn_myLocation:     '我的位置',

      filter_provider: '运营商',
      filter_type:     '类型',
      filter_minHeads: '最少充电头',
      filter_any:      '全部',
      filter_reset:    '↺ 重置',

      sort_prefix:   '排序：',
      sort_default:  '默认',
      sort_distance: '距离',
      sort_heads:    '充电头最多',

      list_head_stations: '站点',
      list_head_inView:   '当前视图 {n} 个',
      list_empty_title:   '当前视图没有站点',
      list_empty_body:    '移动或缩小地图，或清除筛选条件。',
      list_showing_cap:   '当前显示 {cap} / {total} 个站点。放大地图可缩小结果范围。',
      btn_directions:     '🧭 导航',
      btn_details:        '📄 详情',
      toggle_list:        '📋 列表',
      toggle_map:         '🗺 地图',
      sidebar_collapse:   '收起侧栏',
      sidebar_expand:     '展开侧栏',

      toast_locating:        '正在定位…',
      toast_nearYou:         '正在显示你附近的站点',
      toast_nearMeFirst:     "请先点击“附近”，再按距离排序。",
      toast_geoNotSupported: '当前浏览器不支持定位。',
      toast_geoError:        '无法获取你的位置：{error}',

      station_not_found:         '找不到站点',
      station_back:              '← 返回地图',
      station_chargers:          '充电设备（{n}）',
      station_charger_label:     '台充电设备',
      station_head_label:        '个充电头',
      station_get_directions:    '🧭 获取导航',
      station_copy_link:         '🔗 复制链接',
      station_share:             '📤 分享',
      station_charging_capacity: '充电容量',
      station_dc_fast:           'DC 快充',
      station_ac:                'AC 慢充',
      station_total_heads:       '总充电头',
      station_reviews:           '评价',
      station_write_review:      '写评价',
      station_your_name:         '你的姓名',
      station_name_placeholder:  '例如：王先生',
      station_rating:            '评分',
      station_experience:        '使用体验',
      station_exp_placeholder:   '充电速度、稳定性、配套设施、停车情况等有用信息…',
      station_submit:            '提交评价',
      station_approval_notice:   '评价通过管理员审核后显示。',
      station_no_reviews_title:  '暂无评价',
      station_no_reviews_body:   '成为第一个分享充电体验的人。',
      station_based_on:          '基于 {n} 条评价',
      station_review_submitted:  '评价已提交，等待管理员审核',
      station_link_copied:       '链接已复制',
      station_please_rate:       '请选择评分（1-5 星）',
      station_unnamed_charger:   '未命名充电设备',
      station_you_are_here:      '你在这里',
      station_gun_label:         '枪口 {n}',
      station_day_price:         '白天',
      station_night_price:       '夜间',
      station_price_missing:     '价格未提供',
      station_price_unit_kwh:    'kWh',
      station_kw_label:          '{kw} kW',

      time_just_now: '刚刚',
      time_m_ago:    '{n} 分钟前',
      time_h_ago:    '{n} 小时前',
      time_d_ago:    '{n} 天前',

      admin_login_title:    '🔒 管理员登录',
      admin_login_subtitle: '输入管理员密码以管理网站。',
      admin_password:       '密码',
      admin_sign_in:        '登录',
      admin_default_hint:   '💡 第一次使用？默认密码是 <code>admin</code>。登录后请立即修改。',

      admin_tab_dashboard: '📊 仪表盘',
      admin_tab_pending:   '⏳ 待审核评价',
      admin_tab_approved:  '✅ 已通过评价',
      admin_tab_brand:     '🎨 品牌与 Logo',
      admin_tab_settings:  '⚙️ 设置',
      admin_tab_language:  '🌐 语言',

      admin_total_stations:   '总站点数',
      admin_pending_label:    '待审核评价',
      admin_approved_label:   '已通过评价',
      admin_avg_rating:       '平均评分',
      admin_recent_activity:  '最近活动',
      admin_no_activity:      '暂无活动。',

      admin_all_clear:    '全部处理完毕！',
      admin_no_pending:   '没有等待审核的评价。',
      admin_n_pending:    '{n} 条待审核',
      admin_approve:      '✓ 通过',
      admin_reject:       '✕ 拒绝',
      admin_view_page:    '查看页面 →',
      admin_no_approved:  '暂无已通过评价。',
      admin_n_approved:   '{n} 条已通过',
      admin_delete:       '🗑 删除',
      badge_pending:      '待审核',
      badge_approved:     '已通过',

      admin_logo_section:         'Logo',
      admin_no_logo:              '尚未上传 Logo',
      admin_upload_logo:          '⬆️ 上传 Logo',
      admin_remove:               '移除',
      admin_logo_help:            '支持 PNG、JPG、SVG 或 WebP。建议小于 200 KB。Logo 只保存在当前浏览器中，清除网站数据或换浏览器后不会显示。已用存储：',
      admin_header_preview:       '页头预览',
      admin_provider_logos:       '运营商 Logo',
      admin_provider_logos_help:  '每个品牌都可以设置独立 Logo，用于筛选标签和站点标识。',
      admin_no_logo_short:        '无 Logo',
      admin_upload:               '⬆️ 上传',
      admin_brand_name:           '品牌名称',
      admin_save_brand:           '保存品牌名称',

      admin_change_password:  '修改密码',
      admin_current_password: '当前密码',
      admin_new_password:     '新密码',
      admin_update_password:  '更新密码',
      admin_data_management:  '数据管理',
      admin_data_help:        '评价和品牌设置保存在当前浏览器的 localStorage 中。',
      admin_export_data:      '📥 导出全部数据',
      admin_clear_reviews:    '🗑 清空全部评价',

      admin_lang_title:    '语言编辑器',
      admin_lang_subtitle: '编辑泰语、英语和中文翻译。修改会保存在当前浏览器中。',
      admin_lang_save:     '保存翻译',
      admin_lang_reset:    '恢复默认',
      admin_lang_export:   '📥 导出 JSON',
      admin_lang_import:   '📤 导入 JSON',
      admin_lang_col_key:  '键名',
      admin_lang_col_th:   '泰语',
      admin_lang_col_en:   '英语',
      admin_lang_col_zh:   '中文',

      admin_toast_sign_out:      '已退出',
      admin_toast_welcome:       '欢迎回来',
      admin_toast_wrong_pw:      '密码错误',
      admin_toast_pw_updated:    '密码已更新',
      admin_toast_cur_pw_wrong:  '当前密码不正确',
      admin_toast_longer_pw:     '请选择更长的密码',
      admin_toast_exported:      '数据已导出',
      admin_toast_all_deleted:   '全部评价已删除',
      admin_toast_approved:      '评价已通过',
      admin_toast_rejected:      '评价已拒绝',
      admin_toast_deleted:       '评价已删除',
      admin_toast_logo_saved:    'Logo 已保存（{kb} KB）',
      admin_toast_logo_removed:  'Logo 已移除',
      admin_toast_brand_saved:   '品牌名称已保存',
      admin_toast_save_failed:   '保存失败：图片过大，超出浏览器存储限制。请尝试小于 200 KB 的文件。',
      admin_toast_prov_saved:    '{p} Logo 已保存（{kb} KB）',
      admin_toast_trans_saved:   '翻译已保存',
      admin_toast_trans_reset:   '翻译已恢复默认',
      admin_toast_trans_imported:'翻译已导入',

      confirm_delete_review:    '删除这条已通过评价？',
      confirm_clear_all:        '删除全部评价（包括待审核和已通过）？此操作无法撤销。',
      confirm_remove_logo:      '移除当前 Logo？',
      confirm_remove_prov_logo: '移除 {p} Logo？',
      confirm_large_image:      '该图片大小为 {kb} KB，较大的图片可能超出浏览器存储限制。继续？',
      cookie_text:              '本网站使用 Local Storage 在你的设备上保存设置和评价。请阅读<a href="privacy.html">隐私政策</a>和<a href="terms.html">服务条款</a>。',
      cookie_decline:           '拒绝',
      cookie_accept:            '接受',

      lang_btn: 'ไทย',
    },
  };

  // ─── Custom override storage ──────────────────────────────────────
  function getCustom(lang) {
    try { return JSON.parse(localStorage.getItem(KEY_CUSTOM + lang) || '{}'); } catch { return {}; }
  }
  function setCustom(lang, obj) {
    localStorage.setItem(KEY_CUSTOM + lang, JSON.stringify(obj));
  }
  function resetCustom() {
    LANGS.forEach(l => localStorage.removeItem(KEY_CUSTOM + l.code));
  }

  // ─── Language state ───────────────────────────────────────────────
  function getLang() {
    const lang = localStorage.getItem(KEY_LANG) || 'th';
    return STRINGS[lang] ? lang : 'th';
  }
  function setLang(lang) {
    if (!STRINGS[lang]) lang = 'th';
    localStorage.setItem(KEY_LANG, lang);
    document.documentElement.lang = lang;
  }
  function nextLang() {
    const current = getLang();
    const idx = LANGS.findIndex(l => l.code === current);
    return LANGS[(idx + 1) % LANGS.length].code;
  }

  // ─── Translation lookup ───────────────────────────────────────────
  function t(key, vars) {
    const lang = getLang();
    const custom = getCustom(lang);
    let str = Object.prototype.hasOwnProperty.call(custom, key)
      ? custom[key]
      : ((STRINGS[lang] || {})[key] !== undefined ? STRINGS[lang][key] : ((STRINGS['en'] || {})[key] || key));
    if (vars) {
      Object.keys(vars).forEach(k => {
        str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), vars[k]);
      });
    }
    return str;
  }

  // ─── DOM application ─────────────────────────────────────────────
  function apply() {
    document.documentElement.lang = getLang();
    document.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
    });
    // Update language toggle button text on all pages
    document.querySelectorAll('.lang-toggle').forEach(btn => {
      btn.textContent = t('lang_btn');
    });
  }

  // ─── Admin editor helpers ─────────────────────────────────────────
  function getDefaults() { return STRINGS; }

  // Groups for admin editor display
  const GROUPS = [
    { label: 'Navigation',        prefix: 'nav_' },
    { label: 'Header & Search',   keys: ['stats_stations','search_placeholder','btn_nearMe','btn_fitToFiltered','btn_myLocation'] },
    { label: 'Filters',           prefix: 'filter_' },
    { label: 'Sort',              prefix: 'sort_' },
    { label: 'List View',         keys: ['list_head_stations','list_head_inView','list_empty_title','list_empty_body','list_showing_cap','btn_directions','btn_details','toggle_list','toggle_map','sidebar_collapse','sidebar_expand'] },
    { label: 'Toast Messages',    prefix: 'toast_' },
    { label: 'Station Page',      prefix: 'station_' },
    { label: 'Time Format',       prefix: 'time_' },
    { label: 'Admin – Login',     keys: ['admin_login_title','admin_login_subtitle','admin_password','admin_sign_in','admin_default_hint'] },
    { label: 'Admin – Tabs',      keys: ['admin_tab_dashboard','admin_tab_pending','admin_tab_approved','admin_tab_brand','admin_tab_settings','admin_tab_language'] },
    { label: 'Admin – Dashboard', keys: ['admin_total_stations','admin_pending_label','admin_approved_label','admin_avg_rating','admin_recent_activity','admin_no_activity'] },
    { label: 'Admin – Reviews',   keys: ['admin_all_clear','admin_no_pending','admin_n_pending','admin_approve','admin_reject','admin_view_page','admin_no_approved','admin_n_approved','admin_delete','badge_pending','badge_approved'] },
    { label: 'Admin – Brand',     keys: ['admin_logo_section','admin_no_logo','admin_upload_logo','admin_remove','admin_logo_help','admin_header_preview','admin_provider_logos','admin_provider_logos_help','admin_no_logo_short','admin_upload','admin_brand_name','admin_save_brand'] },
    { label: 'Admin – Settings',  keys: ['admin_change_password','admin_current_password','admin_new_password','admin_update_password','admin_data_management','admin_data_help','admin_export_data','admin_clear_reviews'] },
    { label: 'Admin – Language',  keys: ['admin_lang_title','admin_lang_subtitle','admin_lang_save','admin_lang_reset','admin_lang_export','admin_lang_import','admin_lang_col_key','admin_lang_col_th','admin_lang_col_en','admin_lang_col_zh'] },
    { label: 'Admin – Toasts',    prefix: 'admin_toast_' },
    { label: 'Confirm Dialogs',   prefix: 'confirm_' },
    { label: 'Cookie Notice',     prefix: 'cookie_' },
  ];

  function getGroups() { return GROUPS; }
  function getAllKeys() {
    return Object.keys(STRINGS.th);
  }
  function getLanguages() { return LANGS.slice(); }

  return {
    getLang, setLang, nextLang, t, apply,
    getCustom, setCustom, resetCustom,
    getDefaults, getGroups, getAllKeys, getLanguages,
  };
})();
