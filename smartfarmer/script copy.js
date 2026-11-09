// ================= CẤU HÌNH =================
const SUPABASE_URL = 'https://sopqsxhuitqcmnvosjeq.supabase.co';
const SUPABASE_KEY = 'sb_publishable_PdB8mBs-zLvYDpEXP-ds4A_YSktC8lm';
// ============================================

const { createClient } = supabase;
const client = createClient(SUPABASE_URL, SUPABASE_KEY);

// BIẾN TOÀN CỤC
let currentPenId = null;
let envChart = null;
let penNames = {}; // Lưu tên các chuồng để hiển thị trong thông báo
let alertHistory = {}; // Lưu thời gian báo động riêng cho TỪNG chuồng

// --- 1. AUTH ---
async function checkSession() {
    const { data: { session } } = await client.auth.getSession();
    if (session) showDashboard(session.user);
    else toggleAuth('login');
}

function toggleAuth(mode) {
    document.getElementById('dashboard-screen').classList.add('hidden');
    document.getElementById('auth-screen').classList.remove('hidden');
    if (mode === 'login') {
        document.getElementById('login-form').classList.remove('hidden');
        document.getElementById('register-form').classList.add('hidden');
    } else {
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    }
}

async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) alert("Lỗi: " + error.message);
    else checkSession();
}

async function handleRegister() {
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const { data, error } = await client.auth.signUp({ email, password });
    if (error) alert("Lỗi: " + error.message);
    else {
        alert("Đăng ký thành công!");
        checkSession();
    }
}

async function handleLogout() {
    await client.auth.signOut();
    location.reload();
}

// --- 2. DASHBOARD ---
async function showDashboard(user) {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('dashboard-screen').classList.remove('hidden');
    document.getElementById('user-email').innerText = user.email;
    
    // Xin quyền thông báo ngay khi vào
    if ("Notification" in window) Notification.requestPermission();

    // Load danh sách chuồng VÀ Khởi động Rada giám sát toàn cục
    await loadPens(); 
    startGlobalMonitor(); // <--- CHỈ GỌI 1 LẦN DUY NHẤT Ở ĐÂY
}

async function loadPens() {
    const { data: pens } = await client.from('pens').select('*');
    const select = document.getElementById('pen-select');
    select.innerHTML = '';
    penNames = {}; // Reset danh sách tên

    if (pens && pens.length > 0) {
        pens.forEach(p => {
            // Lưu tên chuồng vào bộ nhớ để dùng cho thông báo
            penNames[p.id] = p.name;

            const opt = document.createElement('option');
            opt.value = p.id;
            opt.innerText = p.name;
            select.appendChild(opt);
        });
        currentPenId = pens[0].id;
        loadData(currentPenId);
    } else {
        select.innerHTML = '<option value="">Chưa có chuồng</option>';
    }
}

function changePen() {
    currentPenId = document.getElementById('pen-select').value;
    if(currentPenId) loadData(currentPenId);
    // Lưu ý: Không cần gọi lại Realtime ở đây nữa vì Rada toàn cục đã chạy rồi
}

function loadData(penId) {
    loadEnvironment(penId);
    loadDevices(penId);
    loadAnimals(penId);
}

// --- 3. LOGIC REALTIME (RADA TOÀN CỤC) ---
function startGlobalMonitor() {
    console.log("📡 Đang khởi động Radar..."); // <--- 1. Log lúc khởi động
    
    client.channel('global-farm-monitor')
    .on(
        'postgres_changes', 
        { 
            event: '*', 
            schema: 'public', 
            table: 'env_logs' 
        }, 
        (payload) => {
            console.log("⚡ RADA ĐÃ NHẬN TÍN HIỆU:", payload.new); // <--- 2. Log khi có tin
            
            // Gọi hàm kiểm tra báo động
            checkAlertGlobal(payload.new);

            // Cập nhật giao diện nếu đúng chuồng
            if (newLog.pen_id === currentPenId) {
                updateSensorUI(payload.new);
                updateChartRealtime(payload.new);
            }
        }
    )
    .subscribe((status) => {
        // <--- 3. Log trạng thái kết nối
        console.log("TRẠNG THÁI RADA:", status); 
    });
}

// --- 4. HỆ THỐNG CẢNH BÁO ĐỘC LẬP ---
function checkAlertGlobal(data) {
    // --- CẤU HÌNH NGƯỠNG BÁO ĐỘNG ---
    const THRESHOLDS = {
        temp: 35,    // Nhiệt độ > 35°C là báo động
        hum: 90,     // Độ ẩm > 90% là báo động
        smell: 400   // Độ mùi > 400ppm là báo động (Tùy chỉnh theo cảm biến của bạn)
    };
    const ALERT_COOLDOWN = 60000; // 1 phút báo lại 1 lần nếu vẫn còn lỗi
    
    // Tạo danh sách các vấn đề đang gặp phải
    let problems = [];

    if (data.temperature >= THRESHOLDS.temp) {
        problems.push(`Nhiệt độ cao (${data.temperature}°C)`);
    }
    if (data.humidity >= THRESHOLDS.hum) {
        problems.push(`Độ ẩm cao (${data.humidity}%)`);
    }
    if ((data.smell_level || 0) >= THRESHOLDS.smell) {
        problems.push(`Mùi hôi (${data.smell_level}ppm)`);
    }

    // Nếu có ít nhất 1 vấn đề -> Xử lý gửi thông báo
    if (problems.length > 0) {
        const now = Date.now();
        const lastTime = alertHistory[data.pen_id] || 0;

        if (now - lastTime > ALERT_COOLDOWN) {
            const penName = penNames[data.pen_id] || data.pen_id;
            
            // Nối các lỗi lại thành 1 câu thông báo
            // VD: "Nhiệt độ cao (36°C), Độ ẩm cao (95%)"
            const msgBody = problems.join(', ') + ". Kiểm tra ngay!";
            
            sendBrowserNotification(`⚠️ BÁO ĐỘNG: ${penName}`, msgBody);
            
            // Lưu thời gian báo
            alertHistory[data.pen_id] = now;
        }
    }
}

function sendBrowserNotification(title, body) {
    // 1. Kiểm tra trình duyệt hỗ trợ
    if (!("Notification" in window)) {
        console.error("❌ Trình duyệt này không hỗ trợ thông báo!");
        return;
    }

    // 2. Kiểm tra quyền
    if (Notification.permission === "granted") {
        console.log("✅ Đang gửi thông báo:", title); // Log để biết code đã chạy tới đây
        new Notification(title, { 
            body: body, 
            icon: "https://cdn-icons-png.flaticon.com/512/10336/10336582.png"
        });
    } else if (Notification.permission === "denied") {
        console.warn("🚫 Bạn đã CHẶN thông báo. Hãy vào cài đặt trình duyệt mở lại!");
    } else {
        console.log("⚠️ Chưa xin quyền thông báo. Hãy bấm nút 'Bật Thông Báo' trên màn hình.");
    }
}
// --- 5. CẬP NHẬT GIAO DIỆN & BIỂU ĐỒ ---
function updateSensorUI(data) {
    // 1. Cập nhật số liệu
    document.getElementById('temp').innerText = data.temperature;
    document.getElementById('hum').innerText = data.humidity;
    document.getElementById('smell').innerText = data.smell_level || 0;

    // 2. Hàm phụ trợ để đổi màu nếu vượt ngưỡng
    const checkColor = (elementId, value, threshold) => {
        const el = document.getElementById(elementId);
        const box = el.parentElement; // Lấy cái hộp chứa số

        if (value >= threshold) {
            el.style.color = '#D32F2F'; // Chữ đỏ đậm
            el.style.fontWeight = 'bold';
            box.style.border = '2px solid red'; // Viền đỏ
            box.style.background = '#ffebee';   // Nền hồng nhạt báo động
        } else {
            // Trả về màu mặc định (lấy từ style.css hoặc set cứng)
            el.style.color = ''; 
            el.style.fontWeight = 'normal';
            box.style.border = 'none';
            // Reset màu nền về mặc định của từng loại
            if(elementId === 'temp') box.style.background = '#fbe9e7';
            else if(elementId === 'hum') box.style.background = '#e3f2fd';
            else box.style.background = '#E8F5E9';
        }
    };

    // 3. Kiểm tra từng chỉ số (Ngưỡng phải khớp với hàm checkAlertGlobal)
    checkColor('temp', data.temperature, 35);
    checkColor('hum', data.humidity, 90);
    checkColor('smell', data.smell_level || 0, 400);
}

function updateChartRealtime(data) {
    if(envChart) {
        const time = new Date(data.created_at).toLocaleTimeString();
        envChart.data.labels.push(time);
        
        // Push dữ liệu mới vào 3 cột tương ứng
        envChart.data.datasets[0].data.push(data.temperature);
        envChart.data.datasets[1].data.push(data.humidity);
        envChart.data.datasets[2].data.push(data.smell_level || 0); // Thêm Mùi
        
        // Giữ biểu đồ sạch (chỉ hiện 15 điểm mới nhất cho đỡ rối mắt vì biểu đồ cột tốn diện tích)
        if (envChart.data.labels.length > 15) {
            envChart.data.labels.shift();
            envChart.data.datasets[0].data.shift();
            envChart.data.datasets[1].data.shift();
            envChart.data.datasets[2].data.shift();
        }
        envChart.update();
    }
}

// --- 6. CÁC HÀM LOAD DỮ LIỆU CŨ (GIỮ NGUYÊN) ---
async function loadEnvironment(penId) {
    const { data: logs } = await client.from('env_logs')
        .select('*').eq('pen_id', penId)
        .order('created_at', { ascending: false }).limit(20);

    if (logs && logs.length > 0) {
        const revLogs = logs.reverse();
        updateSensorUI(revLogs[revLogs.length - 1]);
        renderChart(revLogs);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('envChart').getContext('2d');
    
    // Lấy dữ liệu từ mảng
    const labels = data.map(d => new Date(d.created_at).toLocaleTimeString());
    const temps = data.map(d => d.temperature);
    const hums = data.map(d => d.humidity);
    const smells = data.map(d => d.smell_level || 0); // Lấy thêm độ mùi

    if (envChart) envChart.destroy(); // Xóa biểu đồ cũ nếu có

    envChart = new Chart(ctx, {
        type: 'bar', // <--- ĐỔI THÀNH BIỂU ĐỒ CỘT
        data: {
            labels: labels,
            datasets: [
                { 
                    label: 'Nhiệt độ (°C)', 
                    data: temps, 
                    backgroundColor: '#e53935', // Màu đỏ
                    borderWidth: 1
                },
                { 
                    label: 'Độ ẩm (%)', 
                    data: hums, 
                    backgroundColor: '#1e88e5', // Màu xanh dương
                    borderWidth: 1
                },
                { 
                    label: 'Độ mùi (ppm)', 
                    data: smells, 
                    backgroundColor: '#fdd835', // Màu vàng
                    borderWidth: 1
                }
            ]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true // Trục Y bắt đầu từ 0 cho dễ nhìn
                }
            },
            plugins: {
                legend: { position: 'bottom' } // Đưa chú thích xuống dưới
            }
        }
    });
}

// --- CÁC HÀM CRUD (Thêm/Sửa/Xóa) ---
// (Giữ nguyên các hàm addPen, addDevice, addAnimal, openModal, closeModal, deleteAnimal như file cũ)
// ... BẠN HÃY COPY LẠI CÁC HÀM ĐÓ VÀO DƯỚI ĐÂY ...

// Copy các hàm modal/CRUD từ file cũ vào đây nhé
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

async function addPen() {
    const id = document.getElementById('new-pen-id').value;
    const name = document.getElementById('new-pen-name').value;
    if (!id || !name) return alert("Vui lòng điền đủ thông tin!");
    const { error } = await client.from('pens').insert([{ id, name }]);
    if (error) alert("Lỗi: " + error.message);
    else { closeModal('modal-pen'); loadPens(); }
}

async function addDevice() {
    if(!currentPenId) return alert("Chưa chọn chuồng nào!");
    const id = document.getElementById('new-dev-id').value;
    const name = document.getElementById('new-dev-name').value;
    const pin = document.getElementById('new-dev-pin').value;
    const { error } = await client.from('devices').insert([{ id, name, pin_number: parseInt(pin), pen_id: currentPenId, is_active: false }]);
    if (error) alert("Lỗi: " + error.message);
    else { closeModal('modal-device'); loadDevices(currentPenId); }
}

async function addAnimal() {
    if(!currentPenId) return alert("Chưa chọn chuồng nào!");
    const id = document.getElementById('new-ani-id').value;
    const species = document.getElementById('new-ani-species').value;
    const weight = document.getElementById('new-ani-weight').value;
    const target = document.getElementById('new-ani-target').value;
    const { error } = await client.from('animals').insert([{ id, species, weight: parseFloat(weight), target_weight: parseFloat(target), pen_id: currentPenId }]);
    if (error) alert("Lỗi: " + error.message);
    else { closeModal('modal-animal'); loadAnimals(currentPenId); }
}

async function deleteAnimal(id) {
    if(confirm("Bạn chắc chắn muốn xóa con vật này?")) {
        await client.from('animals').delete().eq('id', id);
        loadAnimals(currentPenId);
    }
}
async function loadDevices(penId) {
    const { data: devices } = await client.from('devices').select('*').eq('pen_id', penId).order('id');
    const container = document.getElementById('device-list');
    container.innerHTML = '';
    if (devices && devices.length > 0) {
        devices.forEach(dev => {
            const btn = document.createElement('div');
            btn.className = `dev-btn ${dev.is_active ? 'active' : 'inactive'}`;
            btn.innerHTML = `<strong>${dev.name}</strong><span>${dev.is_active ? 'ON' : 'OFF'}</span>`;
            btn.onclick = () => toggleDevice(dev.id, !dev.is_active);
            container.appendChild(btn);
        });
    } else {
        container.innerHTML = '<small>Chưa cài đặt thiết bị.</small>';
    }
}

async function toggleDevice(deviceId, status) {
    await client.from('devices').update({ is_active: status }).eq('id', deviceId);
    loadDevices(currentPenId);
}
async function loadAnimals(penId) {
    const { data: animals } = await client.from('animals').select('*').eq('pen_id', penId);
    const tbody = document.getElementById('animal-list');
    tbody.innerHTML = '';
    if (animals && animals.length > 0) {
        animals.forEach(a => {
            let badge = '<span class="badge badge-ok">Ổn</span>';
            if (a.feeding_status === 'Anorexic') badge = '<span class="badge badge-danger">Bỏ ăn</span>';
            else if (a.target_weight && a.weight < a.target_weight * 0.8) badge = '<span class="badge badge-warn">Chậm lớn</span>';
            
            tbody.innerHTML += `<tr>
                <td><b>${a.id}</b></td><td>${a.species}</td>
                <td>${a.weight}kg / ${a.target_weight}kg</td>
                <td>${badge}</td>
                <td><button onclick="deleteAnimal('${a.id}')" style="color:red;border:none;background:none;cursor:pointer;">X</button></td>
            </tr>`;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="5">Chưa có vật nuôi</td></tr>';
    }
}

// Bật thông báo thủ công
function enableNotifications() {
    if (!("Notification" in window)) {
        alert("Trình duyệt không hỗ trợ!");
        return;
    }
    Notification.requestPermission().then((permission) => {
        if (permission === "granted") new Notification("Đã bật thông báo!");
    });
}

// KHỞI CHẠY
checkSession();