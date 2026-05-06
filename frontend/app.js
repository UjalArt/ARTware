const API = '';  // same-origin

function artware() {
  return {
    // ── Auth ──
    isAuthenticated: false,
    token: null,
    user: {},
    loginForm: { email: '', password: '' },
    loginError: '',
    loginLoading: false,

    demoCredentials: [
      { email: 'admin@artware.io', password: 'admin123', role: 'superadmin' },
      { email: 'manager@artware.io', password: 'manager123', role: 'admin' },
      { email: 'operator@artware.io', password: 'operator123', role: 'operator' },
      { email: 'viewer@artware.io', password: 'viewer123', role: 'viewer' },
    ],

    // ── Nav ──
    currentPage: 'dashboard',
    mobileSidebarOpen: false,
    navItems: [
      { id: 'dashboard', label: 'Dashboard', icon: '📊', minRole: 'viewer' },
      { id: 'gateways',  label: 'Gateways',  icon: '📡', minRole: 'viewer' },
      { id: 'devices',   label: 'Devices',   icon: '🔌', minRole: 'viewer' },
      { id: 'profiles',  label: 'Device Profiles', icon: '🗂️', minRole: 'viewer' },
      { id: 'rules',     label: 'Forwarding Rules', icon: '🔀', minRole: 'viewer' },
      { id: 'settings',  label: 'Settings',  icon: '⚙️', minRole: 'operator' },
      { id: 'users',     label: 'Users',     icon: '👥', minRole: 'admin' },
      { id: 'audit',     label: 'Audit Log', icon: '📋', minRole: 'admin' },
    ],

    // ── Data ──
    stats: {},
    recentUplinks: [],
    mapGateways: [],
    chartData: null,
    gateways: [],
    devices: [],
    profiles: [],
    rules: [],
    usersList: [],
    auditLogs: [],

    // ── Modals ──
    modals: { gateway: false, device: false, profile: false, rule: false, user: false },
    gatewayForm: {},
    deviceForm: {},
    profileForm: {},
    ruleForm: {},
    userForm: {},

    // ── Settings ──
    settings: {
      chirpstack_url: '', chirpstack_token: '',
      tb_url: '', tb_user: '', tb_pass: '',
    },
    brokerStatus: {},

    // ── Misc ──
    uplinkChart: null,
    refreshTimer: null,

    // ═══════════════════════════ INIT ═══════════════════════════
    async init() {
      const savedToken = localStorage.getItem('artware_token');
      const savedUser  = localStorage.getItem('artware_user');
      if (savedToken && savedUser) {
        this.token = savedToken;
        this.user  = JSON.parse(savedUser);
        this.isAuthenticated = true;
        await this.loadAll();
        this.startAutoRefresh();
      }
    },

    // ═══════════════════════════ AUTH ═══════════════════════════
    async login() {
      this.loginError = '';
      this.loginLoading = true;
      try {
        const form = new URLSearchParams();
        form.append('username', this.loginForm.email);
        form.append('password', this.loginForm.password);
        const res = await fetch(`${API}/api/auth/login`, { method: 'POST', body: form });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Login failed'); }
        const data = await res.json();
        this.token = data.access_token;
        this.user  = data.user;
        localStorage.setItem('artware_token', this.token);
        localStorage.setItem('artware_user', JSON.stringify(this.user));
        this.isAuthenticated = true;
        await this.loadAll();
        this.startAutoRefresh();
      } catch(e) { this.loginError = e.message; }
      finally { this.loginLoading = false; }
    },

    quickLogin(cred) {
      this.loginForm.email = cred.email;
      this.loginForm.password = cred.password;
      this.login();
    },

    logout() {
      this.isAuthenticated = false;
      this.token = null;
      this.user  = {};
      localStorage.removeItem('artware_token');
      localStorage.removeItem('artware_user');
      if (this.refreshTimer) clearInterval(this.refreshTimer);
      this.currentPage = 'dashboard';
    },

    // ═══════════════════════════ API HELPERS ════════════════════
    async api(method, path, body) {
      const opts = {
        method,
        headers: { 'Authorization': `Bearer ${this.token}`, 'Content-Type': 'application/json' },
      };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(`${API}${path}`, opts);
      if (res.status === 401) { this.logout(); return null; }
      if (!res.ok) { const e = await res.json().catch(()=>({detail:'Request failed'})); throw new Error(e.detail||'Error'); }
      if (res.status === 204) return null;
      return res.json();
    },

    get: (path) => { throw ''; },   // replaced below
    post(path, body)   { return this.api('POST',   path, body); },
    put(path, body)    { return this.api('PUT',    path, body); },
    del(path)          { return this.api('DELETE', path); },

    // ═══════════════════════════ LOAD ALL ═══════════════════════
    async loadAll() {
      await Promise.all([
        this.loadDashboard(),
        this.loadGateways(),
        this.loadDevices(),
        this.loadProfiles(),
        this.loadRules(),
        this.loadUsers(),
        this.loadAuditLog(),
      ]);
    },

    async loadDashboard() {
      try {
        const [stats, uplinks, mapGw, chart] = await Promise.all([
          this.api('GET', '/api/dashboard/stats'),
          this.api('GET', '/api/dashboard/uplinks/recent'),
          this.api('GET', '/api/dashboard/gateways/map'),
          this.api('GET', '/api/dashboard/uplinks/chart'),
        ]);
        this.stats = stats || {};
        this.recentUplinks = uplinks || [];
        this.mapGateways = mapGw || [];
        if (chart) this.renderChart(chart);
      } catch(e) { console.error('loadDashboard', e); }
    },

    renderChart(data) {
      const ctx = document.getElementById('uplinkChart');
      if (!ctx) return;
      if (this.uplinkChart) { this.uplinkChart.destroy(); }
      this.uplinkChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Uplinks',
            data: data.counts,
            backgroundColor: 'rgba(0, 179, 179, 0.3)',
            borderColor: 'rgba(0, 200, 200, 0.8)',
            borderWidth: 1,
            borderRadius: 4,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: 'rgba(160,220,220,0.5)', font: { size: 10 } }, grid: { color: 'rgba(0,200,200,0.07)' } },
            y: { ticks: { color: 'rgba(160,220,220,0.5)', font: { size: 10 } }, grid: { color: 'rgba(0,200,200,0.07)' }, beginAtZero: true },
          }
        }
      });
    },

    async loadGateways()  { try { this.gateways = await this.api('GET', '/api/gateways/') || []; } catch(e) {} },
    async loadDevices()   { try { this.devices  = await this.api('GET', '/api/devices/')  || []; } catch(e) {} },
    async loadProfiles()  { try { this.profiles = await this.api('GET', '/api/profiles/') || []; } catch(e) {} },
    async loadRules()     { try { this.rules    = await this.api('GET', '/api/rules/')    || []; } catch(e) {} },
    async loadUsers()     { try { this.usersList = await this.api('GET', '/api/users/')   || []; } catch(e) {} },
    async loadAuditLog()  { try { this.auditLogs = await this.api('GET', '/api/users/audit-log') || []; } catch(e) {} },

    startAutoRefresh() {
      if (this.refreshTimer) clearInterval(this.refreshTimer);
      this.refreshTimer = setInterval(() => {
        this.loadDashboard();
        if (this.currentPage !== 'dashboard') {
          if (this.currentPage === 'gateways') this.loadGateways();
          if (this.currentPage === 'devices')  this.loadDevices();
        }
      }, 10000);
    },

    // ═══════════════════════════ NAV ════════════════════════════
    navigate(page) {
      this.currentPage = page;
      if (page === 'dashboard') { setTimeout(() => this.loadDashboard(), 50); }
      if (page === 'users')     this.loadUsers();
      if (page === 'audit')     this.loadAuditLog();
    },

    currentPageTitle() {
      const item = this.navItems.find(i => i.id === this.currentPage);
      return item ? item.icon + '  ' + item.label : '';
    },

    // ═══════════════════════════ RBAC ═══════════════════════════
    roleLevel() {
      return { superadmin: 4, admin: 3, operator: 2, viewer: 1 }[this.user.role] || 0;
    },
    canAccess(minRole) {
      return this.roleLevel() >= ({ superadmin: 4, admin: 3, operator: 2, viewer: 1 }[minRole] || 0);
    },

    // ═══════════════════════════ GATEWAYS ═══════════════════════
    openGatewayModal(gw) {
      this.gatewayForm = gw
        ? { id: gw.id, name: gw.name, eui: gw.eui, model: gw.model, mqtt_topic_pattern: gw.mqtt_topic_pattern, lat: gw.lat, lon: gw.lon }
        : { id: null, name: '', eui: '', model: 'RAK WisGate Edge Lite 2', mqtt_topic_pattern: 'application/+/device/+/rx', lat: null, lon: null };
      this.modals.gateway = true;
    },
    async saveGateway() {
      try {
        const body = { name: this.gatewayForm.name, eui: this.gatewayForm.eui, model: this.gatewayForm.model,
                       mqtt_topic_pattern: this.gatewayForm.mqtt_topic_pattern,
                       lat: this.gatewayForm.lat || null, lon: this.gatewayForm.lon || null };
        if (this.gatewayForm.id) await this.put(`/api/gateways/${this.gatewayForm.id}`, body);
        else                     await this.post('/api/gateways/', body);
        this.modals.gateway = false;
        await this.loadGateways();
      } catch(e) { alert(e.message); }
    },
    async deleteGateway(id) {
      if (!confirm('Delete this gateway?')) return;
      try { await this.del(`/api/gateways/${id}`); await this.loadGateways(); }
      catch(e) { alert(e.message); }
    },

    // ═══════════════════════════ DEVICES ════════════════════════
    openDeviceModal(d) {
      this.deviceForm = d
        ? { id: d.id, name: d.name, dev_eui: d.dev_eui, gateway_id: d.gateway_id, profile_id: d.profile_id }
        : { id: null, name: '', dev_eui: '', gateway_id: null, profile_id: null };
      this.modals.device = true;
    },
    async saveDevice() {
      try {
        const body = { name: this.deviceForm.name, dev_eui: this.deviceForm.dev_eui,
                       gateway_id: this.deviceForm.gateway_id || null, profile_id: this.deviceForm.profile_id || null };
        if (this.deviceForm.id) await this.put(`/api/devices/${this.deviceForm.id}`, body);
        else                    await this.post('/api/devices/', body);
        this.modals.device = false;
        await this.loadDevices();
      } catch(e) { alert(e.message); }
    },
    async deleteDevice(id) {
      if (!confirm('Delete this device?')) return;
      try { await this.del(`/api/devices/${id}`); await this.loadDevices(); }
      catch(e) { alert(e.message); }
    },

    // ═══════════════════════════ PROFILES ═══════════════════════
    get manufacturers() {
      return [...new Set(this.profiles.map(p => p.manufacturer))].sort();
    },
    openProfileModal() {
      this.profileForm = { name: '', manufacturer: '', model: '', description: '', decoder_key: 'passthrough', icon: '📡' };
      this.modals.profile = true;
    },
    async saveProfile() {
      try {
        await this.post('/api/profiles/', this.profileForm);
        this.modals.profile = false;
        await this.loadProfiles();
      } catch(e) { alert(e.message); }
    },
    async deleteProfile(id) {
      if (!confirm('Delete this custom profile?')) return;
      try { await this.del(`/api/profiles/${id}`); await this.loadProfiles(); }
      catch(e) { alert(e.message); }
    },

    // ═══════════════════════════ RULES ══════════════════════════
    openRuleModal() {
      this.ruleForm = { name: '', device_id: null, profile_id: null, target_type: 'webhook', target_url: '', is_active: true };
      this.modals.rule = true;
    },
    async saveRule() {
      try {
        await this.post('/api/rules/', { ...this.ruleForm, device_id: this.ruleForm.device_id || null, profile_id: this.ruleForm.profile_id || null });
        this.modals.rule = false;
        await this.loadRules();
      } catch(e) { alert(e.message); }
    },
    async toggleRule(r) {
      try { await this.put(`/api/rules/${r.id}`, { is_active: !r.is_active }); await this.loadRules(); }
      catch(e) { alert(e.message); }
    },
    async deleteRule(id) {
      if (!confirm('Delete this rule?')) return;
      try { await this.del(`/api/rules/${id}`); await this.loadRules(); }
      catch(e) { alert(e.message); }
    },

    // ═══════════════════════════ USERS ══════════════════════════
    openUserModal() {
      this.userForm = { id: null, email: '', full_name: '', password: '', role: 'viewer' };
      this.modals.user = true;
    },
    openEditUserModal(u) {
      this.userForm = { id: u.id, email: u.email, full_name: u.full_name, role: u.role };
      this.modals.user = true;
    },
    async saveUser() {
      try {
        if (this.userForm.id) await this.put(`/api/users/${this.userForm.id}`, { full_name: this.userForm.full_name, role: this.userForm.role });
        else await this.post('/api/users/', { email: this.userForm.email, full_name: this.userForm.full_name, password: this.userForm.password, role: this.userForm.role });
        this.modals.user = false;
        await this.loadUsers();
      } catch(e) { alert(e.message); }
    },
    async deleteUser(id) {
      if (!confirm('Delete this user?')) return;
      try { await this.del(`/api/users/${id}`); await this.loadUsers(); }
      catch(e) { alert(e.message); }
    },

    // ═══════════════════════════ UTILS ══════════════════════════
    isMobile() { return window.innerWidth < 768; },

    fmtTime(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      const now = new Date();
      const diff = (now - d) / 1000;
      if (diff < 60)   return 'just now';
      if (diff < 3600) return Math.floor(diff/60) + 'm ago';
      if (diff < 86400)return d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
      return d.toLocaleDateString([], { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
    },

    fmtDate(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleDateString([], { year:'numeric', month:'short', day:'numeric' });
    },

    async loadBrokerStatus() {
      try { this.brokerStatus = await this.api('GET', '/api/broker/status') || {}; }
      catch(e) { this.brokerStatus = { status: 'error' }; }
    },

    fmtUptime(s) {
      if (!s) return '—';
      if (s < 60)   return s + 's';
      if (s < 3600) return Math.floor(s/60) + 'm';
      return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
    },
  };
}
