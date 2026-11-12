// ================= CẤU HÌNH =================
const SUPABASE_URL = 'https://sopqsxhuitqcmnvosjeq.supabase.co';
const SUPABASE_KEY = 'sb_publishable_PdB8mBs-zLvYDpEXP-ds4A_YSktC8lm';
// ============================================

const { createClient } = supabase;
const client = createClient(SUPABASE_URL, SUPABASE_KEY);

// BIẾN TOÀN CỤC
let currentPenId = null;
let envChart = null;
let penNames = {}; 

// [MỚI] BIẾN QUẢN LÝ BÁO ĐỘNG TẬP TRUNG
let activeAlerts = {}; // Lưu danh sách lỗi của từng chuồng: { 'CHUONG_01': ['Nóng', 'Ẩm'] }
const ALARM_SOUND = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); // Âm thanh
let currentAlertIndex = 0;
let currentHealthAnimalId = null; // Lưu ID con vật đang khám
let weightChart = null; // Biến lưu biểu đồ
let currentTrackingAnimalId = null; // Lưu ID con đang chọn
let currentMode = 'livestock'; // Mặc định là Chăn nuôi ('livestock' hoặc 'cultivation')
let currentCropId = null; 
let cropChart = null;
// --- 1. KHỞI ĐỘNG HỆ THỐNG ---
// --- QUẢN LÝ PHIÊN ĐĂNG NHẬP (FIX LỖI F5 BỊ OUT) ---
async function initAuth() {
    // 1. Lắng nghe mọi sự kiện đăng nhập/đăng xuất/F5
    client.auth.onAuthStateChange((event, session) => {
        console.log("🔐 Auth Event:", event);
        
        if (session) {
            // Nếu có phiên đăng nhập -> Vào Dashboard ngay
            showDashboard(session.user);
        } else {
            // Nếu không -> Đá về trang login
            toggleAuth('login');
        }
    });
}

async function showDashboard(user) {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('dashboard-screen').classList.remove('hidden');
    document.getElementById('user-email').innerText = user.email;
    
    // Xin quyền thông báo
    if ("Notification" in window) Notification.requestPermission();

    await loadPens(); 
    await loadInventory();
    // Kích hoạt 2 luồng song song:
    startGlobalMonitor(); // 1. Luồng nhận dữ liệu (Rada)
    startAlarmLoop();     // 2. Luồng báo động (Loa phường) - [MỚI]
}

// --- 2. LOGIC BÁO ĐỘNG LIÊN TỤC (ALARM LOOP) ---
// Hàm này chạy độc lập, cứ 5 giây kiểm tra biến activeAlerts một lần
// --- 2. LOGIC BÁO ĐỘNG LUÂN PHIÊN (ROUND ROBIN) ---
function startAlarmLoop() {
    setInterval(() => {
        // Lấy danh sách các chuồng đang bị lỗi (VD: ['CHUONG_A', 'CHUONG_B'])
        const problemPens = Object.keys(activeAlerts);
        
        // Nếu không có lỗi nào -> Im lặng
        if (problemPens.length === 0) return;

        // 1. Phát âm thanh "Bíp"
        ALARM_SOUND.play().catch(() => {});

        // 2. Logic Xoay Vòng
        // Nếu chỉ số vượt quá danh sách (do có chuồng vừa được sửa xong) -> Reset về 0
        if (currentAlertIndex >= problemPens.length) {
            currentAlertIndex = 0;
        }

        // Lấy ra chuồng cần báo động LẦN NÀY
        const penId = problemPens[currentAlertIndex];
        const issues = activeAlerts[penId]; // Lấy danh sách lỗi (Nóng, Ẩm...)
        const penName = penNames[penId] || penId; // Lấy tên hiển thị

        // 3. Gửi thông báo
        // VD: "🔥 BÁO ĐỘNG (1/2): Chuồng Gà"
        const title = `🔥 BÁO ĐỘNG (${currentAlertIndex + 1}/${problemPens.length}): ${penName}`;
        const body = `Đang gặp lỗi: ${issues.join(', ')}. Hãy kiểm tra ngay!`;
        
        sendContinuousNotification(title, body);

        // 4. Tăng chỉ số để lần sau báo chuồng tiếp theo
        currentAlertIndex++;

    }, 5000); // Cứ 5 giây chuyển sang báo chuồng tiếp theo
}

function sendContinuousNotification(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { 
            body: body, 
            tag: 'farm-alert', // [QUAN TRỌNG] Tag này giúp thông báo mới thay thế thông báo cũ chứ không xếp chồng
            icon: "https://cdn-icons-png.flaticon.com/512/10336/10336582.png",
            requireInteraction: true // Bắt buộc người dùng phải bấm tắt mới ẩn
        });
    }
}

// --- 3. RADA GIÁM SÁT (NHẬN DỮ LIỆU & CẬP NHẬT TRẠNG THÁI) ---
function startGlobalMonitor() {
    console.log("📡 Rada đang quét...");
    
    client.channel('global-farm-monitor')
    .on(
        'postgres_changes', 
        { event: '*', schema: 'public', table: 'env_logs' }, 
        (payload) => {
            const newLog = payload.new;
            
            // [MỚI] Cập nhật trạng thái vào danh sách báo động
            updateAlertStatus(newLog);

            // Cập nhật giao diện nếu đang xem đúng chuồng đó
            if (newLog.pen_id === currentPenId) {
                updateSensorUI(newLog);
                updateChartRealtime(newLog);
            }
        }
    )
    .subscribe();
}

// Hàm phân tích dữ liệu -> Ghi vào sổ đen (activeAlerts)
function updateAlertStatus(data) {
    let THRESHOLDS = {};

    // CẤU HÌNH NGƯỠNG RIÊNG BIỆT
    if (currentMode === 'livestock') {
        // --- NGƯỠNG CHO VẬT NUÔI ---
        THRESHOLDS = { 
            temp: 35,   // Quá 35 độ là nóng
            hum: 90,    // Quá 90% là ẩm ướt
            sensor3: 400 // Quá 400ppm là hôi
        }; 
    } else {
        // --- NGƯỠNG CHO CÂY TRỒNG ---
        THRESHOLDS = { 
            temp: 40,   // Cây chịu nhiệt tốt hơn chút
            hum: 95,    // Cây ưa ẩm
            sensor3: 30 // Độ ẩm Đất: Nếu DƯỚI 30% là KHÔ HẠN (Logic ngược)
        }; 
    }

    let issues = [];
    if (data.temperature >= THRESHOLDS.temp) issues.push(`Nóng (${data.temperature}°C)`);
    if (data.humidity >= THRESHOLDS.hum) issues.push(`Ẩm cao (${data.humidity}%)`);
    
    // Logic báo động cho cảm biến thứ 3
    if (currentMode === 'livestock') {
        if ((data.smell_level || 0) >= THRESHOLDS.sensor3) issues.push(`Mùi hôi (${data.smell_level})`);
    } else {
        // Với cây trồng, ta báo động khi Đất bị KHÔ (thấp hơn ngưỡng)
        if ((data.smell_level || 0) <= THRESHOLDS.sensor3) issues.push(`Đất khô (${data.smell_level}%)`);
    }

    if (issues.length > 0) {
        activeAlerts[data.pen_id] = issues;
    } else {
        delete activeAlerts[data.pen_id];
    }
}

// --- 4. CÁC HÀM GIAO DIỆN & CRUD (GIỮ NGUYÊN NHƯ CŨ) ---
// (Phần này chỉ copy lại code cũ, không đổi logic, nhưng tôi viết lại đầy đủ để bạn copy 1 lần cho tiện)

function toggleAuth(mode) {
    const authScreen = document.getElementById('auth-screen');
    const dashboard = document.getElementById('dashboard-screen');
    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');

    if(mode === 'login') {
        authScreen.classList.remove('hidden');
        dashboard.classList.add('hidden');
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
    } else if (mode === 'register') {
        authScreen.classList.remove('hidden');
        dashboard.classList.add('hidden');
        loginForm.classList.add('hidden');
        regForm.classList.remove('hidden');
    }
}

async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) alert(error.message); else initAuth()    ;
}

async function handleRegister() {
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const { error } = await client.auth.signUp({ email, password });
    if (error) alert(error.message); else { alert("Đăng ký thành công!"); initAuth(); }
}

async function handleLogout() { await client.auth.signOut(); location.reload(); }

async function loadPens() {
    // [SỬA] Chỉ lấy chuồng theo chế độ hiện tại (type = currentMode)
    const { data: pens } = await client.from('pens')
        .select('*')
        .eq('type', currentMode); // <--- QUAN TRỌNG

    const select = document.getElementById('pen-select');
    select.innerHTML = '';
    penNames = {}; 

    if (pens && pens.length > 0) {
        pens.forEach(p => {
            penNames[p.id] = p.name;
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.innerText = p.name;
            select.appendChild(opt);
        });
        currentPenId = pens[0].id;
        loadData(currentPenId);
    } else {
        select.innerHTML = '<option value="">(Trống)</option>';
        // Xóa dữ liệu cũ nếu không có chuồng/vườn nào
        document.getElementById('temp').innerText = '--';
        document.getElementById('device-list').innerHTML = '';
        document.getElementById('animal-list').innerHTML = '';
        document.querySelector('.card.full-width .table-responsive').innerHTML = currentMode === 'livestock' ? 
            '<table id="animal-table">...</table>' : '<div id="crop-list">Chưa có cây trồng</div>';
    }
}

function changePen() {
    currentPenId = document.getElementById('pen-select').value;
    if(currentPenId) loadData(currentPenId);
}

function loadData(penId) {
    loadEnvironment(penId);
    loadDevices(penId);
    
    // [SỬA] Kiểm tra chế độ để tải dữ liệu phù hợp
    if (currentMode === 'livestock') {
        // Hiện bảng vật nuôi, ẩn bảng cây (nếu có logic ẩn hiện)
        loadAnimals(penId);
    } else {
        loadCrops(penId); // Hàm mới tải cây trồng
    }
}

// Cập nhật UI màu sắc
function updateSensorUI(data) {
    document.getElementById('temp').innerText = data.temperature;
    document.getElementById('hum').innerText = data.humidity;
    document.getElementById('smell').innerText = data.smell_level || 0;

    const checkColor = (id, val, limit) => {
        const el = document.getElementById(id);
        const box = el.parentElement;
        if (val >= limit) {
            el.style.color = '#D32F2F'; el.style.fontWeight = 'bold';
            box.style.border = '2px solid red'; box.style.background = '#ffebee';
        } else {
            el.style.color = ''; el.style.fontWeight = 'normal';
            box.style.border = 'none'; 
            if(id==='temp') box.style.background='#fbe9e7';
            else if(id==='hum') box.style.background='#e3f2fd';
            else box.style.background='#E8F5E9';
        }
    };
    checkColor('temp', data.temperature, 35);
    checkColor('hum', data.humidity, 90);
    checkColor('smell', data.smell_level || 0, 400);
}

// Biểu đồ CỘT
function updateChartRealtime(data) {
    if(envChart) {
        const time = new Date(data.created_at).toLocaleTimeString();
        envChart.data.labels.push(time);
        envChart.data.datasets[0].data.push(data.temperature);
        envChart.data.datasets[1].data.push(data.humidity);
        envChart.data.datasets[2].data.push(data.smell_level || 0);
        if (envChart.data.labels.length > 15) {
            envChart.data.labels.shift();
            envChart.data.datasets[0].data.shift();
            envChart.data.datasets[1].data.shift();
            envChart.data.datasets[2].data.shift();
        }
        envChart.update();
    }
}

async function loadEnvironment(penId) {
    const { data: logs } = await client.from('env_logs').select('*').eq('pen_id', penId).order('created_at', { ascending: false }).limit(20);
    if (logs && logs.length > 0) {
        const rev = logs.reverse();
        updateSensorUI(rev[rev.length - 1]);
        renderChart(rev);
        // Kiểm tra ngay khi load xem có lỗi không để báo luôn
        updateAlertStatus(rev[rev.length - 1]);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('envChart').getContext('2d');
    
    // Lấy dữ liệu
    const labels = data.map(d => new Date(d.created_at).toLocaleTimeString());
    const temps = data.map(d => d.temperature);
    const hums = data.map(d => d.humidity);
    const sensor3 = data.map(d => d.smell_level || 0); // Đây là cột dữ liệu thứ 3

    if (envChart) envChart.destroy();

    // Xác định nhãn cho cột thứ 3 dựa trên chế độ
    const label3 = currentMode === 'livestock' ? 'Độ mùi (ppm)' : 'Độ ẩm đất (%)';
    const color3 = currentMode === 'livestock' ? '#fdd835' : '#795548'; // Vàng cho Mùi, Nâu cho Đất

    envChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { 
                    label: 'Nhiệt độ (°C)', 
                    data: temps, 
                    backgroundColor: '#e53935' 
                },
                { 
                    label: 'Độ ẩm KK (%)', 
                    data: hums, 
                    backgroundColor: '#1e88e5' 
                },
                { 
                    label: label3, // <--- Nhãn động
                    data: sensor3, 
                    backgroundColor: color3 // <--- Màu động
                }
            ]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

// --- CRUD ---
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
async function addPen() { /* ... Giữ nguyên logic cũ ... */ 
    const id = document.getElementById('new-pen-id').value;
    const name = document.getElementById('new-pen-name').value;
    if (!id || !name) return alert("Thiếu thông tin");
    const { error } = await client.from('pens').insert([{id, name}]);
    if(error) alert(error.message); else { closeModal('modal-pen'); loadPens(); }
}
async function addDevice() {
    if(!currentPenId) return alert("Chọn chuồng đi!");
    const id=document.getElementById('new-dev-id').value;
    const name=document.getElementById('new-dev-name').value;
    const pin=document.getElementById('new-dev-pin').value;
    const {error}=await client.from('devices').insert([{id, name, pin_number:parseInt(pin), pen_id:currentPenId}]);
    if(error) alert(error.message); else { closeModal('modal-device'); loadDevices(currentPenId); }
}
async function addAnimal() {
    const id=document.getElementById('new-ani-id').value;
    const species=document.getElementById('new-ani-species').value;
    const w=document.getElementById('new-ani-weight').value;
    const t=document.getElementById('new-ani-target').value;
    const {error}=await client.from('animals').insert([{id, species, weight:parseFloat(w), target_weight:parseFloat(t), pen_id:currentPenId}]);
    if(error) alert(error.message); else { closeModal('modal-animal'); loadAnimals(currentPenId); }
}
async function deleteAnimal(id) {
    if(confirm("Xóa nhé?")) { await client.from('animals').delete().eq('id', id); loadAnimals(currentPenId); }
}
async function loadDevices(penId) {
    const { data: devs } = await client.from('devices').select('*').eq('pen_id', penId).order('id');
    const div = document.getElementById('device-list'); div.innerHTML='';
    if(devs) devs.forEach(d => {
        const btn = document.createElement('div');
        btn.className = `dev-btn ${d.is_active?'active':'inactive'}`;
        btn.innerHTML = `<strong>${d.name}</strong><span>${d.is_active?'ON':'OFF'}</span>`;
        btn.onclick = () => toggleDevice(d.id, !d.is_active);
        div.appendChild(btn);
    });
}
async function toggleDevice(id, status) {
    await client.from('devices').update({is_active:status}).eq('id', id); loadDevices(currentPenId);
}
async function loadAnimals(penId) {
    const { data: animals } = await client.from('animals').select('*').eq('pen_id', penId);
    const tbody = document.getElementById('animal-list');
    tbody.innerHTML = '';
    
    if (animals && animals.length > 0) {
        animals.forEach(a => {
            // Logic tạo Badge trạng thái (Giữ nguyên)
            let badge = '<span class="badge badge-ok">Ổn</span>';
            if (a.feeding_status === 'Anorexic') badge = '<span class="badge badge-danger">Bỏ ăn</span>';
            else if (a.target_weight && a.weight < a.target_weight * 0.8) badge = '<span class="badge badge-warn">Còi</span>';
            
            // --- SỬA DÒNG NÀY ---
            tbody.innerHTML += `<tr>
                <td><b>${a.id}</b></td>
                <td>${a.species}</td>
                <td>${a.weight}kg <span style="color:#888; font-size:0.8em">/ ${a.target_weight}kg</span></td>
                <td>${badge}</td>
                <td style="display:flex; gap:5px;">
                    <button onclick="openTracking('${a.id}')" title="Biểu đồ cân nặng" style="cursor:pointer; background:#e3f2fd; border:1px solid #2196f3; color:#0d47a1; border-radius:4px; padding:4px 8px;">📈</button>
                    
                    <button onclick="openHealth('${a.id}')" title="Nhật ký thú y" style="cursor:pointer; background:#ffebee; border:1px solid #ef5350; color:#c62828; border-radius:4px; padding:4px 8px;">🚑</button>
                    
                    <button onclick="deleteAnimal('${a.id}')" title="Xóa" style="color:#666;border:none;background:none;cursor:pointer; font-weight:bold;">🗑️</button>
                </td>
            </tr>`;
            // --------------------
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Chưa có vật nuôi</td></tr>';
    }
}
function enableNotifications() {
    if(!("Notification" in window)) return alert("Trình duyệt không hỗ trợ");
    Notification.requestPermission().then(p => { if(p==='granted') new Notification("Đã bật thông báo!"); });
    // Kích hoạt âm thanh giả để trình duyệt cho phép phát tiếng sau này
    ALARM_SOUND.play().then(() => ALARM_SOUND.pause()).catch(() => {});
}
// --- MODULE NHẬT KÝ THÚ Y ---

// 1. Mở Modal & Tải dữ liệu
async function openHealth(animalId) {
    currentHealthAnimalId = animalId;
    document.getElementById('health-title').innerText = `🏥 Sức Khỏe: ${animalId}`;
    openModal('modal-health');
    loadHealthLogs(animalId);
}

// 2. Tải danh sách ghi chép
async function loadHealthLogs(animalId) {
    const { data: logs } = await client
        .from('health_logs')
        .select('*')
        .eq('animal_id', animalId)
        .order('created_at', { ascending: false }); // Mới nhất lên đầu

    const tbody = document.getElementById('health-list');
    tbody.innerHTML = '';

    if (logs && logs.length > 0) {
        logs.forEach(log => {
            // Định dạng màu sắc theo loại
            let typeBadge = '';
            if (log.type === 'Vaccine') typeBadge = '<span class="badge" style="background:#e8f5e9; color:#2e7d32;">💉 Vắc-xin</span>';
            else if (log.type === 'Treatment') typeBadge = '<span class="badge" style="background:#fff3e0; color:#ef6c00;">💊 Điều trị</span>';
            else typeBadge = '<span class="badge" style="background:#ffebee; color:#c62828;">🚑 Bệnh</span>';

            const date = new Date(log.created_at).toLocaleDateString('vi-VN') + ' ' + new Date(log.created_at).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'});

            tbody.innerHTML += `
                <tr>
                    <td style="font-size:12px; color:#555;">${date}</td>
                    <td>${typeBadge}</td>
                    <td>
                        <strong>${log.title}</strong><br>
                        <span style="font-size:12px; color:#666;">${log.note || ''}</span>
                    </td>
                    <td>
                        <button onclick="deleteHealthLog(${log.id})" style="color:red; border:none; background:none; cursor:pointer;">&times;</button>
                    </td>
                </tr>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:#888;">Chưa có ghi chép y tế nào.</td></tr>';
    }
}

// 3. Thêm ghi chép mới
async function addHealthLog() {
    const type = document.getElementById('health-type').value;
    const title = document.getElementById('health-action').value;
    const note = document.getElementById('health-note').value;

    if (!title) return alert("Vui lòng nhập tên bệnh hoặc tên thuốc!");

    const { error } = await client
        .from('health_logs')
        .insert([{ 
            animal_id: currentHealthAnimalId, 
            type: type, 
            title: title, 
            note: note 
        }]);

    if (error) alert("Lỗi: " + error.message);
    else {
        // Reset form và tải lại danh sách
        document.getElementById('health-action').value = '';
        document.getElementById('health-note').value = '';
        loadHealthLogs(currentHealthAnimalId);
    }
}

// 4. Xóa ghi chép
async function deleteHealthLog(id) {
    if (confirm("Xóa ghi chép này?")) {
        await client.from('health_logs').delete().eq('id', id);
        loadHealthLogs(currentHealthAnimalId);
    }
}
// --- MODULE TRACKING & CẬP NHẬT CÂN NẶNG ---

// 1. Mở Modal & Tải dữ liệu lịch sử
async function openTracking(animalId) {
    currentTrackingAnimalId = animalId;
    document.getElementById('track-title').innerText = `📈 Lịch sử: ${animalId}`;
    openModal('modal-tracking');
    
    // Tải lịch sử từ Supabase
    const { data: logs } = await client
        .from('weight_logs')
        .select('*')
        .eq('animal_id', animalId)
        .order('created_at', { ascending: true }); // Cũ nhất đến mới nhất

    renderWeightChart(logs || []);
}

// 2. Chức năng QUAN TRỌNG: Lưu cân nặng mới
async function saveNewWeight() {
    const newWeight = parseFloat(document.getElementById('new-log-weight').value);
    
    if (!newWeight || newWeight <= 0) return alert("Vui lòng nhập cân nặng hợp lệ!");

    // A. Thêm vào bảng lịch sử (weight_logs)
    const { error: logError } = await client
        .from('weight_logs')
        .insert([{ 
            animal_id: currentTrackingAnimalId, 
            weight: newWeight 
        }]);

    if (logError) return alert("Lỗi lưu lịch sử: " + logError.message);

    // B. Cập nhật cân nặng hiện tại vào bảng vật nuôi (animals)
    const { error: updateError } = await client
        .from('animals')
        .update({ weight: newWeight })
        .eq('id', currentTrackingAnimalId);

    if (updateError) {
        alert("Lỗi cập nhật con vật: " + updateError.message);
    } else {
        alert("✅ Đã cập nhật cân nặng thành công!");
        document.getElementById('new-log-weight').value = ''; // Xóa ô nhập
        
        // Cập nhật lại giao diện ngay lập tức
        openTracking(currentTrackingAnimalId); // Vẽ lại biểu đồ
        loadAnimals(currentPenId); // Cập nhật số cân ở danh sách ngoài
    }
}

// 3. Hàm vẽ biểu đồ (Dùng thư viện Chart.js đã có)
function renderWeightChart(logs) {
    const ctx = document.getElementById('weightChart').getContext('2d');
    
    // Tạo dữ liệu cho trục X (Ngày) và Trục Y (Cân nặng)
    const labels = logs.map(l => new Date(l.created_at).toLocaleDateString('vi-VN'));
    const dataPoints = logs.map(l => l.weight);

    if (weightChart) weightChart.destroy(); // Xóa biểu đồ cũ

    weightChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cân nặng (kg)',
                data: dataPoints,
                borderColor: '#2E7D32', // Màu xanh lá cây
                backgroundColor: 'rgba(46, 125, 50, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#2E7D32',
                pointRadius: 5,
                fill: true,
                tension: 0.3 // Đường cong mềm mại
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: false, title: { display: true, text: 'Kg' } }
            },
            plugins: {
                legend: { display: false } // Ẩn chú thích cho gọn
            }
        }
    });
}
// ================= MODULE QUẢN LÝ KHO (NÂNG CẤP BỘ LỌC) =================

// Biến lưu trữ tạm thời (Cache) để lọc nhanh không cần gọi lại Server
let allInventoryData = []; 

// 1. Tải dữ liệu từ Server (Chỉ chạy 1 lần khi mở web hoặc sau khi nhập/xuất)
async function loadInventory() {
    const list = document.getElementById('inventory-list');
    list.innerHTML = '<p style="text-align:center; color:#888;">⏳ Đang tải kho...</p>';

    const { data: items, error } = await client.from('inventory').select('*').order('category').order('name');

    if (error) {
        list.innerHTML = `<p style="color:red">Lỗi: ${error.message}</p>`;
        return;
    }

    // Lưu vào biến toàn cục để dành lọc
    allInventoryData = items || [];
    
    // Hiển thị toàn bộ lần đầu
    renderInventoryList(allInventoryData);
}

// 2. Hàm lọc (Chạy ngay khi gõ phím)
function filterInventory() {
    const searchText = document.getElementById('inv-search').value.toLowerCase();
    const categoryFilter = document.getElementById('inv-filter-cat').value;

    // Lọc dữ liệu từ biến Cache
    const filteredItems = allInventoryData.filter(item => {
        // Điều kiện 1: Tên phải chứa từ khóa tìm kiếm
        const matchName = item.name.toLowerCase().includes(searchText);
        
        // Điều kiện 2: Loại phải khớp (hoặc chọn Tất cả)
        const matchCat = categoryFilter === 'All' || item.category === categoryFilter;

        return matchName && matchCat;
    });

    // Vẽ lại danh sách đã lọc
    renderInventoryList(filteredItems);
}

// 3. Hàm vẽ giao diện (Dùng chung cho cả Load và Filter)
function renderInventoryList(items) {
    const list = document.getElementById('inventory-list');
    list.innerHTML = '';

    if (!items || items.length === 0) {
        list.innerHTML = '<p style="text-align:center; color:#999; padding:20px;">Không tìm thấy vật tư nào.</p>';
        return;
    }

    // Nhóm theo loại để hiển thị cho đẹp
    let currentCat = '';
    
    // Sắp xếp lại danh sách lọc theo loại để nhóm cho đẹp
    items.sort((a, b) => a.category.localeCompare(b.category));

    items.forEach(item => {
        // Tiêu đề nhóm (Thức ăn / Phân bón)
        if (item.category !== currentCat) {
            currentCat = item.category;
            const catName = currentCat === 'Feed' ? '🥩 Thức ăn' : (currentCat === 'Fertilizer' ? '🌱 Phân bón' : '🛠️ Khác');
            list.innerHTML += `<div style="background:#eee; padding:5px 10px; margin:5px 0; font-weight:bold; font-size:13px; border-radius:4px;">${catName}</div>`;
        }

        // Cảnh báo hết hàng
        let color = '#333';
        let warningIcon = '';
        
        if (item.quantity <= 0) {
            color = 'red';
            warningIcon = '⚠️ HẾT';
        } else if (item.quantity <= 5) {
            color = '#E65100'; // Cam đậm
            warningIcon = '⚡ Sắp hết';
        }

        list.innerHTML += `
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #eee; font-size:14px;">
                <span>${item.name}</span>
                <div style="text-align:right;">
                    <span style="font-weight:bold; color:${color}; margin-right:5px;">
                        ${item.quantity} ${item.unit}
                    </span>
                    <span style="font-size:10px; color:red; font-weight:bold;">${warningIcon}</span>
                </div>
            </div>
        `;
    });
}
// 2. Xử lý NHẬP KHO
function openImportModal() { openModal('modal-import'); }

async function processImport() {
    const category = document.getElementById('imp-category').value;
    const name = document.getElementById('imp-name').value;
    const qty = parseFloat(document.getElementById('imp-qty').value);
    const unit = document.getElementById('imp-unit').value || 'kg';
    const price = parseFloat(document.getElementById('imp-price').value) || 0;

    if (!name || !qty) return alert("Vui lòng nhập tên và số lượng!");

    // Kiểm tra hàng đã có chưa
    const { data: existing } = await client.from('inventory')
        .select('*').eq('name', name).eq('category', category).maybeSingle();

    let error;
    if (existing) {
        // Nếu có rồi -> Cộng dồn số lượng
        const { error: err } = await client.from('inventory')
            .update({ quantity: existing.quantity + qty, unit_price: price })
            .eq('id', existing.id);
        error = err;
    } else {
        // Nếu chưa -> Tạo mới
        const { error: err } = await client.from('inventory')
            .insert([{ name, category, quantity: qty, unit, unit_price: price }]);
        error = err;
    }

    if (error) alert("Lỗi nhập kho: " + error.message);
    else {
        // Lưu lịch sử nhập
        await client.from('inventory_logs').insert([{ item_name: name, action_type: 'IMPORT', amount: qty, note: 'Nhập hàng mới' }]);
        alert("✅ Đã nhập kho thành công!");
        closeModal('modal-import');
        loadInventory();
    }
}

// 3. Xử lý XUẤT KHO (Dùng)
async function openExportModal() {
    openModal('modal-export');
    
    // Tải danh sách vật tư vào Select
    const { data: items } = await client.from('inventory').select('*').gt('quantity', 0);
    const select = document.getElementById('exp-select');
    select.innerHTML = '';
    
    if (items && items.length > 0) {
        items.forEach(i => {
            const opt = document.createElement('option');
            opt.value = i.id;
            opt.setAttribute('data-qty', i.quantity);
            opt.setAttribute('data-cat', i.category); // Lưu loại để check
            opt.setAttribute('data-name', i.name);
            opt.innerText = `${i.name} (Còn: ${i.quantity} ${i.unit})`;
            select.appendChild(opt);
        });
        checkExportType(); // Kiểm tra ngay mục đầu tiên
    } else {
        select.innerHTML = '<option>Kho hết hàng!</option>';
    }

    // Tải danh sách chuồng (để chọn nếu là thức ăn)
    const { data: pens } = await client.from('pens').select('*');
    const penSelect = document.getElementById('exp-pen-select');
    penSelect.innerHTML = '';
    if(pens) pens.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.innerText = p.name;
        penSelect.appendChild(opt);
    });
}

// Hàm phụ: Nếu chọn Thức ăn thì hiện ô chọn chuồng, Phân bón thì ẩn đi
function checkExportType() {
    const select = document.getElementById('exp-select');
    if(select.selectedIndex < 0) return;
    
    const option = select.options[select.selectedIndex];
    const category = option.getAttribute('data-cat');
    const penDiv = document.getElementById('exp-pen-div');

    if (category === 'Feed') {
        penDiv.classList.remove('hidden'); // Hiện ô chọn chuồng
    } else {
        penDiv.classList.add('hidden');    // Ẩn đi
    }
}

async function processExport() {
    const select = document.getElementById('exp-select');
    const qty = parseFloat(document.getElementById('exp-qty').value);
    const note = document.getElementById('exp-note').value;
    
    if (!qty || qty <= 0) return alert("Số lượng không hợp lệ!");
    if (select.selectedIndex < 0) return;

    const option = select.options[select.selectedIndex];
    const id = option.value;
    const currentQty = parseFloat(option.getAttribute('data-qty'));
    const name = option.getAttribute('data-name');
    const category = option.getAttribute('data-cat');

    if (qty > currentQty) return alert("Không đủ hàng trong kho!");

    // Xác định Pen ID (chỉ lấy nếu là Thức ăn)
    let penId = null;
    if (category === 'Feed') {
        penId = document.getElementById('exp-pen-select').value;
    }

    // 1. Trừ kho
    const { error } = await client.from('inventory')
        .update({ quantity: currentQty - qty })
        .eq('id', id);

    if (error) return alert("Lỗi xuất kho: " + error.message);

    // 2. Lưu lịch sử
    await client.from('inventory_logs').insert([{
        item_name: name,
        action_type: 'EXPORT',
        amount: qty,
        pen_id: penId, // Sẽ là null nếu là Phân bón
        note: note || (category === 'Feed' ? 'Cho ăn' : 'Sử dụng')
    }]);

    alert(`✅ Đã xuất ${qty} ${name}`);
    closeModal('modal-export');
    loadInventory();
}
// --- LOGIC CHUYỂN ĐỔI CHẾ ĐỘ ---
function switchMode(mode) {
    currentMode = mode;

    // 1. Đổi màu nút
    document.getElementById('btn-mode-livestock').className = mode === 'livestock' ? 'btn-mode active' : 'btn-mode';
    document.getElementById('btn-mode-cultivation').className = mode === 'cultivation' ? 'btn-mode active' : 'btn-mode';

    // 2. Ẩn/Hiện vùng hiển thị
    const livestockView = document.getElementById('livestock-view');
    const cultivationView = document.getElementById('cultivation-view');
    const title = document.getElementById('main-title'); // Tiêu đề thẻ Card
    const addBtn = document.getElementById('main-add-btn'); // Nút thêm
    
    // [MỚI] Lấy phần tử đơn vị của cảm biến thứ 3 để đổi tên
    const sensor3Unit = document.querySelector('.sensor-box.smell .unit');
    const sensor3Box = document.querySelector('.sensor-box.smell');

    if (mode === 'livestock') {
        // --- CHẾ ĐỘ CHĂN NUÔI ---
        if(title) title.innerHTML = '🐖 Đàn Nuôi';
        if(addBtn) {
            addBtn.innerHTML = '+ Thêm Con Vật';
            addBtn.onclick = () => openModal('modal-animal');
        }
        
        // Đổi hiển thị cảm biến về "Mùi"
        if(sensor3Unit) sensor3Unit.innerText = 'ppm';
        if(sensor3Box) {
            sensor3Box.style.background = '#E8F5E9'; // Màu xanh nhạt mặc định
            sensor3Box.title = "Độ mùi hôi chuồng trại";
        }

        livestockView.classList.remove('hidden');   
        cultivationView.classList.add('hidden');    
    } else {
        // --- CHẾ ĐỘ TRỒNG TRỌT ---
        if(title) title.innerHTML = '🌿 Vườn Cây';
        if(addBtn) {
            addBtn.innerHTML = '+ Thêm Cây Trồng';
            addBtn.onclick = () => openModal('modal-crop');
        }

        // Đổi hiển thị cảm biến thành "Đất" (Độ ẩm đất)
        if(sensor3Unit) sensor3Unit.innerText = '% Đất';
        if(sensor3Box) {
            sensor3Box.style.background = '#FFF3E0'; // Màu cam nhạt cho đất
            sensor3Box.title = "Độ ẩm đất";
        }
        
        livestockView.classList.add('hidden');      
        cultivationView.classList.remove('hidden'); 
    }

    // 3. Tải lại danh sách khu vực (Sẽ tự động tải lại môi trường của khu vực đó)
    loadPens();
}
// --- MODULE TRỒNG TRỌT (CROPS) ---

// 1. Thêm khu vực (Chuồng hoặc Vườn) - Cập nhật hàm addPen cũ
async function addPen() {
    const id = document.getElementById('new-pen-id').value;
    const name = document.getElementById('new-pen-name').value;
    const type = document.getElementById('new-pen-type').value; // Lấy loại

    if (!id || !name) return alert("Thiếu thông tin");
    
    const { error } = await client.from('pens').insert([{ id, name, type }]);
    
    if (error) alert("Lỗi: " + error.message);
    else { 
        closeModal('modal-pen'); 
        // Nếu thêm đúng loại đang xem thì reload, không thì thôi
        if(type === currentMode) loadPens(); 
        else alert(`Đã thêm ${name} vào bên ${type === 'livestock' ? 'Chăn nuôi' : 'Trồng trọt'}!`);
    }
}

// 2. Thêm Cây Trồng
async function addCrop() {
    if (!currentPenId) return alert("Chưa chọn vườn!");
    const name = document.getElementById('crop-name').value;
    const qty = document.getElementById('crop-qty').value;
    const date = document.getElementById('crop-date').value;

    const { error } = await client.from('crops').insert([{
        pen_id: currentPenId,
        name: name,
        quantity: parseInt(qty),
        plant_date: date
    }]);

    if(error) alert(error.message);
    else { closeModal('modal-crop'); loadCrops(currentPenId); }
}

// 3. Tải danh sách cây trồng
async function loadCrops(penId) {
    const { data: crops } = await client.from('crops').select('*').eq('pen_id', penId);
    const container = document.getElementById('crop-list');
    
    if (!crops || crops.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:20px; color:#888; width:100%;">🌱 Chưa trồng cây nào trong vườn này.</p>';
        return;
    }

    let html = '';
    crops.forEach(c => {
        // Tính số ngày tuổi
        const days = Math.floor((new Date() - new Date(c.plant_date)) / (1000 * 60 * 60 * 24));
        
        html += `
        <div style="background:white; padding:20px; border-radius:12px; border:1px solid #eee; box-shadow: 0 4px 10px rgba(0,0,0,0.03); transition:0.3s;">
            <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:10px;">
                <div>
                    <h4 style="margin:0; color:#2E7D32; font-size:18px;">${c.name}</h4>
                    <span style="font-size:12px; color:#888;">Gieo ngày: ${new Date(c.plant_date).toLocaleDateString('vi-VN')}</span>
                </div>
                <span class="badge" style="background:#E8F5E9; color:#2E7D32; font-size:13px;">${days} ngày tuổi</span>
            </div>
            
            <div style="font-size:14px; color:#555; margin-bottom: 5px;">
                📦 Số lượng gốc: <b>${c.quantity}</b>
            </div>

            <div class="crop-actions">
                <button onclick="openCropTracking(${c.id})" class="btn-action btn-track">
                    📈 Phát triển
                </button>
                <button onclick="openCropCare(${c.id})" class="btn-action btn-care">
                    💧 Chăm sóc
                </button>
                <button onclick="deleteCrop(${c.id})" class="btn-action btn-delete-icon" title="Phá bỏ cây này">
                    🗑️
                </button>
            </div>
        </div>
        `;
    });
    
    // Bọc trong grid để hiển thị đẹp hơn
    container.innerHTML = `<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:20px;">${html}</div>`;
}

async function deleteCrop(id) {
    if(confirm("Bạn muốn phá bỏ cây này?")) {
        await client.from('crops').delete().eq('id', id);
        loadCrops(currentPenId);
    }
}
// ================= MODULE CÂY TRỒNG (TRACKING & CARE) =================

// --- A. THEO DÕI PHÁT TRIỂN (TRACKING) ---
async function openCropTracking(cropId) {
    currentCropId = cropId;
    document.getElementById('crop-track-title').innerText = `📈 Cây số #${cropId}`;
    openModal('modal-crop-tracking');
    
    // Tải dữ liệu kích thước
    const { data: logs } = await client.from('crop_growth_logs')
        .select('*').eq('crop_id', cropId).order('created_at', { ascending: true });
    
    renderCropChart(logs || []);
}

async function saveCropGrowth() {
    const size = parseFloat(document.getElementById('new-crop-size').value);
    if (!size) return alert("Nhập kích thước!");

    const { error } = await client.from('crop_growth_logs')
        .insert([{ crop_id: currentCropId, size: size }]);
        
    if (error) alert(error.message);
    else {
        alert("Đã lưu!");
        document.getElementById('new-crop-size').value = '';
        openCropTracking(currentCropId); // Vẽ lại chart
    }
}

function renderCropChart(logs) {
    // Kiểm tra xem Modal có đang mở và Canvas có tồn tại không
    const canvas = document.getElementById('cropChart');
    if (!canvas) return; 

    const ctx = canvas.getContext('2d');
    const labels = logs.map(l => new Date(l.created_at).toLocaleDateString('vi-VN'));
    const dataPoints = logs.map(l => l.size);

    // [QUAN TRỌNG] Kiểm tra biến cropChart trước khi destroy
    if (typeof cropChart !== 'undefined' && cropChart) {
        cropChart.destroy();
    }

    cropChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Kích thước (cm)',
                data: dataPoints,
                borderColor: '#4CAF50', // Màu xanh lá
                backgroundColor: 'rgba(76, 175, 80, 0.2)',
                borderWidth: 2,
                pointRadius: 4,
                fill: true, 
                tension: 0.3
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true } // Luôn bắt đầu từ 0 để dễ nhìn
            }
        }
    });
}

// --- B. NHẬT KÝ CHĂM SÓC (CARE) ---
async function openCropCare(cropId) {
    currentCropId = cropId;
    openModal('modal-crop-care');
    loadCropCareLogs(cropId);
}

async function loadCropCareLogs(cropId) {
    const { data: logs } = await client.from('crop_care_logs')
        .select('*').eq('crop_id', cropId).order('created_at', { ascending: false });
    
    const list = document.getElementById('crop-care-list');
    list.innerHTML = '';
    
    if (logs) logs.forEach(l => {
        let icon = '📝';
        if(l.type === 'Water') icon = '💧 Tưới';
        else if(l.type === 'Fertilizer') icon = '🧪 Phân';
        else if(l.type === 'Pesticide') icon = '⚠️ Thuốc';
        else if(l.type === 'Prune') icon = '✂️ Tỉa';

        const time = new Date(l.created_at).toLocaleString('vi-VN');
        list.innerHTML += `
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:8px; color:#2E7D32; font-weight:bold;">${icon}</td>
                <td style="padding:8px;">${l.note || ''}<br><small style="color:#888;">${time}</small></td>
            </tr>
        `;
    });
}

async function addCropCareLog() {
    const type = document.getElementById('care-type').value;
    const note = document.getElementById('care-note').value;
    
    const { error } = await client.from('crop_care_logs')
        .insert([{ crop_id: currentCropId, type, note }]);
        
    if(error) alert(error.message);
    else {
        document.getElementById('care-note').value = '';
        loadCropCareLogs(currentCropId);
    }
}
initAuth();