
        let currentTab = 'dashboard';
        let ws;
        let hotelState = {};
        let twin;
        let evacChart, performanceChart, fireForecastChart, bottleneckChart;
        function init() {
            twin = new DigitalTwin('digital-twin-container');
            initWebSocket();
            startTime();
            initCharts();
            initMap();
            initVisionSimulation();
            initForecastingCharts();
            setMapFloor(2); // Set default floor state
        }

        let mapCanvas, mapCtx;
        function initMap() {
            mapCanvas = document.getElementById('ops-map');
            if (!mapCanvas) return;
            mapCtx = mapCanvas.getContext('2d');
            window.addEventListener('resize', resizeMap);
            resizeMap();
            animateMap();
        }

        function resizeMap() {
            if (!mapCanvas || !mapCanvas.parentElement) return;
            const rect = mapCanvas.parentElement.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                mapCanvas.width = rect.width;
                mapCanvas.height = rect.height;
            }
        }

        let currentMapFloor = 2; // Default to F2

        function setMapFloor(floor) {
            currentMapFloor = floor;
            
            // Update UI buttons
            for(let i=0; i<=4; i++) {
                const btn = document.getElementById(`btn-fl-${i}`);
                if (btn) {
                    if (i === floor) {
                        btn.classList.add('bg-accent', 'text-black');
                        btn.classList.remove('hover:bg-white/5');
                    } else {
                        btn.classList.remove('bg-accent', 'text-black');
                        btn.classList.add('hover:bg-white/5');
                    }
                }
            }
            
            // Update Title
            const title = document.getElementById('map-title');
            if (title) {
                title.innerText = floor === 0 ? 'LIVE OPERATIONS MAP - GRND FLOOR' : `LIVE OPERATIONS MAP - FLOOR ${floor}`;
            }
        }
        let guestPositions = [];
        let staffPositions = [];

        function animateMap() {
            if (!mapCtx || currentTab !== 'staff') {
                requestAnimationFrame(animateMap);
                return;
            }

            mapCtx.clearRect(0, 0, mapCanvas.width, mapCanvas.height);
            
            const w = mapCanvas.width;
            const h = mapCanvas.height;
            const padX = w * 0.15;
            const padY = h * 0.2;
            const floorW = w - 2 * padX;
            const floorH = h - 2 * padY;
            const corridorH = floorH * 0.3;
            const roomH = (floorH - corridorH) / 2;
            const roomW = floorW / 5;

            // Draw Corridors
            mapCtx.fillStyle = 'rgba(30, 41, 59, 0.8)';
            mapCtx.fillRect(padX, padY + roomH, floorW, corridorH);
            
            // Draw Rooms
            mapCtx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
            mapCtx.lineWidth = 1;
            mapCtx.textAlign = 'center';
            mapCtx.textBaseline = 'middle';
            mapCtx.font = '9px Inter';
            
            const getRoomColor = (roomId) => {
                if (!lastAssessment) return 'rgba(15, 23, 42, 0.9)'; // Default dark
                const fireZones = lastAssessment.fire_spread ? lastAssessment.fire_spread.etas || {} : {};
                const floor = parseInt(roomId.slice(0, -2));
                const floorRisk = lastAssessment.zone_risk_scores ? lastAssessment.zone_risk_scores[floor] || 0 : 0;
                
                // If the room is actively on fire or in immediate path (ETA < 5m)
                if (fireZones[roomId] !== undefined) {
                    const eta = fireZones[roomId];
                    if (eta < 5) return 'rgba(239, 68, 68, 0.6)'; // Red
                    return 'rgba(245, 158, 11, 0.6)'; // Orange/Yellow
                }
                // If the floor is high risk or guest is actively evacuating
                const guestData = lastAssessment.hotel_data?.guests?.[roomId];
                if (floorRisk > 60 || (guestData && guestData.status === 'EVACUATING')) return 'rgba(245, 158, 11, 0.3)'; // Faded Yellow
                // Safe / monitored
                return 'rgba(16, 185, 129, 0.2)'; // Green
            };

            for(let i=0; i<5; i++) {
                // Top row
                const rxTop = padX + i * roomW;
                const ryTop = padY;
                const roomNumTop = i + 1;
                const roomIdTop = `${currentMapFloor}${roomNumTop < 10 ? '0'+roomNumTop : roomNumTop}`;
                
                mapCtx.fillStyle = getRoomColor(roomIdTop);
                mapCtx.fillRect(rxTop, ryTop, roomW, roomH);
                mapCtx.strokeRect(rxTop, ryTop, roomW, roomH);
                mapCtx.fillStyle = 'rgba(255,255,255,0.8)';
                mapCtx.fillText(roomIdTop, rxTop + roomW/2, ryTop + roomH/2);

                // Bottom row
                const ryBot = padY + roomH + corridorH;
                const roomNumBot = i + 6;
                const roomIdBot = `${currentMapFloor}${roomNumBot < 10 ? '0'+roomNumBot : roomNumBot}`;
                
                mapCtx.fillStyle = getRoomColor(roomIdBot);
                mapCtx.fillRect(rxTop, ryBot, roomW, roomH);
                mapCtx.strokeRect(rxTop, ryBot, roomW, roomH);
                mapCtx.fillStyle = 'rgba(255,255,255,0.8)';
                mapCtx.fillText(roomIdBot, rxTop + roomW/2, ryBot + roomH/2);
            }

            // Draw Exits
            mapCtx.fillStyle = 'rgba(16, 185, 129, 0.15)';
            mapCtx.fillRect(padX - 50, padY + roomH, 50, corridorH);
            mapCtx.fillRect(padX + floorW, padY + roomH, 50, corridorH);
            mapCtx.fillStyle = 'rgba(16, 185, 129, 0.9)';
            mapCtx.fillText("EXIT L", padX - 25, padY + roomH + corridorH/2);
            mapCtx.fillText("EXIT R", padX + floorW + 25, padY + roomH + corridorH/2);

            // Draw Danger Zones (dynamic based on assessment)
            if (lastAssessment && lastAssessment.fire_spread && lastAssessment.fire_spread.etas) {
                const fireRooms = Object.keys(lastAssessment.fire_spread.etas).filter(id => parseInt(id.slice(0, -2)) === currentMapFloor);
                
                fireRooms.forEach(roomId => {
                    const rNum = parseInt(roomId.slice(-2));
                    const rIdx = rNum <= 5 ? rNum - 1 : rNum - 6;
                    const isTop = rNum <= 5;
                    const fx = padX + rIdx * roomW + roomW / 2;
                    const fy = isTop ? padY + roomH/2 : padY + roomH + corridorH + roomH/2;

                    mapCtx.fillStyle = 'rgba(244, 63, 94, 0.25)';
                    mapCtx.beginPath();
                    mapCtx.arc(fx, fy, 35, 0, Math.PI * 2);
                    mapCtx.fill();
                    mapCtx.strokeStyle = 'rgba(244, 63, 94, 0.6)';
                    mapCtx.stroke();
                    mapCtx.fillStyle = 'rgba(244, 63, 94, 1)';
                    mapCtx.fillText("FIRE", fx, fy - 15);
                });
            }

            // Draw Staff & Paths
            staffPositions.forEach((s, idx) => {
                if (s.floor !== currentMapFloor) return; // Only draw staff on this floor
                
                // If they have a target room, calculate exact pixel position
                if (s.targetRoom) {
                    const rNum = parseInt(s.targetRoom.slice(-2));
                    let rIdx = rNum <= 5 ? rNum - 1 : rNum - 6;
                    let isTop = rNum <= 5;
                    s.tx = padX + rIdx * roomW + roomW / 2;
                    s.ty = isTop ? padY + roomH + corridorH/2 : padY + roomH + corridorH/2; // Stand outside the room in the corridor
                } else if (!s.tx || s.tx < padX || s.tx > padX + floorW) {
                    s.tx = padX + Math.random() * floorW;
                    s.ty = padY + roomH + corridorH/2; // wander in corridor
                }

                // Initialize starting positions if not set
                if (!s.x) {
                    s.x = padX + 20 + (idx * 60);
                    s.y = s.ty || (padY + roomH + corridorH/2);
                }

                s.x += (s.tx - s.x) * 0.02;
                s.y += (s.ty - s.y) * 0.02;

                if (!s.targetRoom && Math.abs(s.x - s.tx) < 2 && Math.abs(s.y - s.ty) < 2) {
                    s.tx = padX + Math.random() * floorW;
                    let rand = Math.random();
                    if (rand < 0.3) s.ty = padY + roomH/2;
                    else if (rand < 0.6) s.ty = padY + roomH + corridorH + roomH/2;
                    else s.ty = padY + roomH + corridorH/2;
                }

                // Draw Path
                mapCtx.setLineDash([3, 4]);
                mapCtx.strokeStyle = 'rgba(16, 185, 129, 0.5)';
                mapCtx.beginPath();
                mapCtx.moveTo(s.x, s.y);
                mapCtx.lineTo(s.tx, s.ty);
                mapCtx.stroke();
                mapCtx.setLineDash([]);

                // Draw Dot
                mapCtx.fillStyle = s.color;
                mapCtx.beginPath();
                mapCtx.arc(s.x, s.y, 5, 0, Math.PI * 2);
                mapCtx.fill();
                
                // Shadow/Glow
                mapCtx.shadowBlur = 12;
                mapCtx.shadowColor = s.color;
                mapCtx.stroke();
                mapCtx.shadowBlur = 0;

                // Label
                mapCtx.fillStyle = 'white';
                mapCtx.font = 'bold 9px Inter';
                mapCtx.fillText(s.id, s.x, s.y - 12);
            });

            // Static Guests (in rooms)
            mapCtx.fillStyle = 'rgba(255,255,255,0.6)';
            for(let i=0; i<8; i++) {
                const gx = padX + (i % 5) * roomW + roomW * 0.3;
                const gy = i < 5 ? padY + roomH * 0.6 : padY + roomH + corridorH + roomH * 0.4;
                mapCtx.beginPath();
                mapCtx.arc(gx, gy, 2, 0, Math.PI * 2);
                mapCtx.fill();
            }

            // Draw Guest Paths (Self-Rescue)
            guestPositions.forEach(g => {
                if (g.floor !== currentMapFloor) return;
                
                if (!g.x) {
                    // Start in their room
                    const rNum = parseInt(g.room.slice(-2));
                    let rIdx = rNum <= 5 ? rNum - 1 : rNum - 6;
                    let isTop = rNum <= 5;
                    g.x = padX + rIdx * roomW + roomW / 2;
                    g.y = isTop ? padY + roomH/2 : padY + roomH + corridorH + roomH/2;
                    // Target is nearest exit
                    g.tx = padX - 20; // Exit L
                    g.ty = padY + roomH + corridorH/2;
                }

                g.x += (g.tx - g.x) * 0.01;
                g.y += (g.ty - g.y) * 0.01;

                // Draw Guest Dot
                mapCtx.fillStyle = '#ffffff';
                mapCtx.beginPath();
                mapCtx.arc(g.x, g.y, 4, 0, Math.PI * 2);
                mapCtx.fill();
                
                // Ring
                mapCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
                mapCtx.beginPath();
                mapCtx.arc(g.x, g.y, 8, 0, Math.PI * 2);
                mapCtx.stroke();
            });

            requestAnimationFrame(animateMap);
        }

        function initVisionSimulation() {
            const container = document.getElementById('camera-grid');
            if (!container) return;
            
            setInterval(() => {
                if (currentTab !== 'vision') return;
                const boxes = container.querySelectorAll('.detection-box');
                boxes.forEach(box => {
                    const top = parseFloat(box.style.top);
                    const left = parseFloat(box.style.left);
                    box.style.top = (top + (Math.random() - 0.5) * 1.5) + '%';
                    box.style.left = (left + (Math.random() - 0.5) * 1.5) + '%';
                });
            }, 200);
        }

        function setView(mode) {
            const grid = document.getElementById('building-matrix');
            const twinCont = document.getElementById('digital-twin-container');
            const btnGrid = document.getElementById('view-btn-grid');
            const btn3d = document.getElementById('view-btn-3d');

            if (mode === 'grid') {
                grid.classList.remove('hidden');
                twinCont.classList.add('hidden');
                btnGrid.classList.add('bg-accent');
                btn3d.classList.remove('bg-accent');
            } else {
                grid.classList.add('hidden');
                twinCont.classList.remove('hidden');
                btnGrid.classList.remove('bg-accent');
                btn3d.classList.add('bg-accent');
                
                if (!twin) {
                    twin = new DigitalTwin('digital-twin-container');
                }
                setTimeout(() => {
                    twin.onResize();
                    twin.renderer.render(twin.scene, twin.camera);
                }, 100);
            }
        }

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById(`btn-${tab}`);
            if (activeBtn) activeBtn.classList.add('active');
            
            ['dashboard', 'vision', 'forecasting', 'staff', 'reports'].forEach(t => {
                const el = document.getElementById(`view-${t}`);
                if (el) el.classList.toggle('hidden', t !== tab);
            });

            if (tab === 'staff' && typeof resizeMap === 'function') setTimeout(resizeMap, 100);
            if (tab === 'vision') fetchAndRenderCameraFeeds();
        }
        window.switchTab = switchTab;

        let lastAssessment = null;

        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/gm`);
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'SYNC' || data.type === 'AI_ASSESSMENT') {
                    updateStats(data.stats);
                    if (data.log) updateTacticalLog(data.log);
                    
                    if (data.assessment) {
                        lastAssessment = data.assessment;
                        hotelState = data.assessment.hotel_data || {};
                        updateStaff(data.assessment.staff_assignments);
                        updateForecasting(data.assessment);
                        updateSOSLog(data.assessment.recent_sos);
                        if (data.camera) updateVisionAI(data.camera);
                        if (twin) twin.updateState(data.assessment);
                    }
                }
            };
            ws.onclose = () => setTimeout(initWebSocket, 2000);
        }

        function updateStats(stats) {
            if (!stats) return;
            document.getElementById('evac-pct').innerText = stats.evacuation_percentage;
            document.getElementById('evac-bar').style.width = stats.evacuation_percentage + '%';
            document.getElementById('active-rescues').innerText = stats.active_rescues;
            document.getElementById('pending-count').innerText = stats.pending_count;
            document.getElementById('completed-count').innerText = stats.completed_count;
            
            // Update Evacuation Timeline Chart
            if (evacChart && stats.history && stats.history.length > 0) {
                evacChart.data.labels = stats.history.map(h => h.time);
                evacChart.data.datasets[0].data = stats.history.map(h => h.percentage);
                evacChart.update('none'); // silent update
            }
            
            // Update Staff Efficiency Chart
            if (performanceChart && stats.efficiency) {
                const labels = Object.keys(stats.efficiency);
                const data = Object.values(stats.efficiency);
                if (labels.length > 0) {
                    performanceChart.data.labels = labels;
                    performanceChart.data.datasets[0].data = data;
                    performanceChart.update();
                }
            }
        }

        function renderBuilding(riskScores = {}) {
            const matrix = document.getElementById('building-matrix');
            if (!matrix) return;
            matrix.innerHTML = '';
            
            const hotelData = hotelState.hotel || {};

            for (let f = 0; f < 5; f++) {
                const floorDiv = document.createElement('div');
                floorDiv.className = 'flex items-center gap-4';
                
                const label = document.createElement('div');
                label.className = 'w-12 text-[10px] font-bold text-slate-500';
                label.innerText = f === 0 ? 'GRND' : `F${f}`;
                floorDiv.appendChild(label);
                
                const roomsDiv = document.createElement('div');
                roomsDiv.className = 'flex gap-1 flex-grow';
                
                for (let r = 1; r <= 10; r++) {
                    const roomId = `${f}${r < 10 ? '0'+r : r}`;
                    const roomInfo = hotelData[f] ? hotelData[f][roomId] : null;
                    const isStaticHighAlert = roomInfo && roomInfo.is_high_alert;

                    const room = document.createElement('div');
                    room.className = 'flex-grow h-12 glass-panel flex flex-col items-center justify-center text-[10px] border-l-4 transition-all duration-500 relative';
                    
                    // Risk color logic
                    let risk = riskScores[f] || 0;
                    const fireZones = lastAssessment?.fire_spread?.etas || {};
                    const isRoomOnFire = fireZones[roomId] !== undefined && fireZones[roomId] < 5;

                    if (isRoomOnFire) {
                        room.style.borderColor = '#f43f5e';
                        room.style.backgroundColor = 'rgba(244, 63, 94, 0.4)';
                        room.classList.add('animate-pulse');
                    }
                    else if (risk > 50 || fireZones[roomId] !== undefined) {
                        room.style.borderColor = '#fbbf24';
                        room.style.backgroundColor = 'rgba(251, 191, 36, 0.2)';
                        room.classList.remove('animate-pulse');
                    }
                    else if (isStaticHighAlert) {
                        room.style.borderColor = '#facc15'; // Amber/Gold for high alert
                        room.style.backgroundColor = 'rgba(250, 204, 21, 0.1)';
                        room.classList.remove('animate-pulse');
                    }
                    else {
                        room.style.borderColor = '#10b981';
                        room.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
                        room.classList.remove('animate-pulse');
                    }
                    
                    room.innerHTML = `
                        <span class="font-bold">${r}</span>
                        ${isStaticHighAlert ? '<span class="text-[6px] text-yellow-500 font-black mt-0.5">ALERT</span>' : ''}
                    `;
                    
                    roomsDiv.appendChild(room);
                }
                floorDiv.appendChild(roomsDiv);
                matrix.appendChild(floorDiv);
            }
        }

        function updateStaff(assignments) {
            const grid = document.getElementById('staff-grid');
            const aiLog = document.getElementById('ai-engine-log');
            if (!grid) return;
            
            if (!assignments || Object.keys(assignments).length === 0) {
                grid.innerHTML = '<div class="text-[10px] text-slate-600 italic p-4 text-center">No active rescues... system monitoring.</div>';
                return;
            }
            
            grid.innerHTML = '';

            // Sync 2D Map Staff Positions
            let activeIds = new Set();
            Object.keys(assignments).forEach(sid => activeIds.add(sid));
            staffPositions = staffPositions.filter(s => activeIds.has(s.id));

            Object.entries(assignments).forEach(([sid, data]) => {
                let s = staffPositions.find(p => p.id === sid);
                if (!s) {
                    s = { id: sid, color: '#fbbf24' };
                    staffPositions.push(s);
                }
                s.floor = parseInt(data.floor);
                s.targetRoom = data.room;

                const card = document.createElement('div');
                card.className = 'glass-panel p-6 flex flex-col gap-4 border-l-4 ' + 
                                (data.status === 'CRITICAL' ? 'border-red-500' : 'border-accent');
                
                card.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div>
                            <p class="text-[10px] font-bold text-slate-500 uppercase">${sid}</p>
                            <h4 class="font-bold text-white">${data.task}</h4>
                        </div>
                        <span class="px-2 py-1 rounded text-[8px] font-black uppercase ${data.status === 'CRITICAL' ? 'bg-red-500/20 text-red-500' : 'bg-accent/20 text-accent'}">
                            ${data.status}
                        </span>
                    </div>
                    <div class="flex items-center gap-4 text-[10px] text-slate-400">
                        <div class="flex items-center gap-1">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                            <span>FL ${data.floor} | RM ${data.room}</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            <span>ETA: ${data.eta}m</span>
                        </div>
                    </div>
                    <button onclick="completeTask('${sid}')" class="w-full py-2 bg-white/5 hover:bg-accent hover:text-black text-[9px] font-black uppercase rounded-lg transition-all border border-white/5">Mark Complete</button>
                    ${data.status === 'CRITICAL' ? `
                        <div class="bg-red-500/10 border border-red-500/20 p-2 rounded text-[9px] text-red-400 font-bold flex items-center gap-2">
                            <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                            PREDICTIVE REROUTE
                        </div>
                    ` : ''}
                    ${data.is_vulnerable ? `
                        <div class="bg-yellow-500/10 border border-yellow-500/20 p-2 rounded text-[9px] text-yellow-400 font-bold flex items-center gap-2">
                            <span class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span>
                            VULNERABLE GUEST
                        </div>
                    ` : ''}
                `;
                grid.appendChild(card);
            });
        }

        async function completeTask(staffId) {
            try {
                const res = await fetch(`/staff/${staffId}/complete`, { method: 'POST' });
                if (res.ok) {
                    console.log(`Task completed by ${staffId}`);
                }
            } catch (err) {
                console.error("Error completing task:", err);
            }
        }

        function updateTacticalLog(log) {
            const aiLogEl = document.getElementById('ai-engine-log');
            if (!log) return;

            // Update Staff View (Chronological narrative, detailed)
            if (aiLogEl) {
                aiLogEl.innerHTML = log.map(entry => {
                    let borderColor = 'border-white/10';
                    let titleColor = 'text-white';
                    
                    if (entry.category === 'INITIATION') {
                        borderColor = 'border-red-500'; titleColor = 'text-red-500 animate-pulse';
                    } else if (entry.category === 'PREDICTION') {
                        borderColor = 'border-yellow-500'; titleColor = 'text-yellow-500';
                    } else if (entry.category === 'RESCUE') {
                        borderColor = 'border-accent'; titleColor = 'text-accent';
                    } else if (entry.category === 'PRE-MEASURE') {
                        borderColor = 'border-blue-500'; titleColor = 'text-blue-400';
                    } else if (entry.category === 'STRATEGIC') {
                        borderColor = 'border-purple-500'; titleColor = 'text-purple-400 font-black italic';
                    }

                    return `
                        <div class="border-l-2 ${borderColor} pl-3 py-1 transition-all">
                            <p class="${titleColor} font-bold text-[11px]">${entry.category || 'SYSTEM'}</p>
                            <p class="text-[9px] text-slate-400">${entry.msg}</p>
                            <p class="text-[8px] text-white/20 mt-1">${entry.time}</p>
                        </div>
                    `;
                }).join('');
            }
        }

        function updateSOSLog(sosEvents) {
            const sosLog = document.getElementById('sos-log');
            if (!sosLog || !sosEvents || sosEvents.length === 0) return;

            sosLog.innerHTML = sosEvents.map(sos => {
                const langColor = sos.detected_language === 'English' ? 'text-slate-400' : 'text-blue-400';
                const sentimentIcon = sos.sentiment === 'Critical' ? '🔴' : '🟡';
                return `
                    <div class="glass-panel p-4 border border-white/5 bg-slate-900/50">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-[9px] font-bold text-white uppercase">${sos.guest} // RM ${sos.room}</span>
                            <span class="px-2 py-0.5 rounded text-[8px] font-black uppercase bg-blue-900/30 ${langColor}">
                                🌐 ${sos.detected_language || 'UNKNOWN'}
                            </span>
                        </div>
                        <p class="text-[12px] font-medium text-white mb-2 italic">"${sos.original_message}"</p>
                        
                        <div class="space-y-2 mt-3 border-t border-white/5 pt-2">
                            <div class="flex items-center justify-between text-[8px] font-black uppercase">
                                <span class="text-slate-500">Gemma Translation</span>
                                <span class="text-accent">${sentimentIcon} ${sos.sentiment || 'URGENT'}</span>
                            </div>
                            <p class="text-[10px] font-bold text-white bg-white/5 p-2 rounded">
                                ${sos.translation || sos.original_message}
                            </p>
                            ${sos.reasoning ? `
                                <div class="bg-blue-500/10 p-2 rounded border border-blue-500/20">
                                    <p class="text-[8px] text-blue-400 font-black uppercase mb-1">✨ Gemma Reasoning</p>
                                    <p class="text-[9px] text-slate-300 leading-tight">${sos.reasoning}</p>
                                </div>
                            ` : ''}
                        </div>
                        <p class="text-[7px] text-slate-600 mt-2 text-right uppercase tracking-widest">${sos.time.split('T')[1].substring(0, 8)}</p>
                    </div>
                `;
            }).join('');
        }

        // Fetch camera feeds from REST API (fallback when WebSocket camera data is missing)
        async function fetchAndRenderCameraFeeds() {
            try {
                const res = await fetch('/camera/feeds');
                if (!res.ok) return;
                const data = await res.json();
                updateVisionAI(data);
        } catch(e) { console.warn('Camera fetch fallback failed:', e); }
        }

        // Poll camera feeds every 3 seconds when on Vision tab
        setInterval(() => {
            if (currentTab === 'vision') fetchAndRenderCameraFeeds();
        }, 3000);

        function updateVisionAI(cameraData) {
            const grid = document.getElementById('camera-grid');
            if (!grid) return;

            if (!cameraData || !cameraData.feeds || (Array.isArray(cameraData.feeds) && cameraData.feeds.length === 0)) {
                grid.innerHTML = '<div class="col-span-full py-20 text-center text-slate-600 italic text-[10px]">No thermal feeds available. Systems may be offline.</div>';
                return;
            }

            let feedsToRender = Array.isArray(cameraData.feeds) ? [...cameraData.feeds] : Object.values(cameraData.feeds);
            feedsToRender = feedsToRender.slice(0, 5);
            feedsToRender.push({
                floor: 'STAIRS',
                status: 'SAFE',
                zone_label: 'CLEAR',
                detections: [],
                gemma_vision: { reasoning: "Scene baseline thermal scan clear. No abnormal heat signatures detected.", inference_time_ms: 12, engine: "Gemma-Thermal-2B" }
            });

            // Update sidebar stats
            const totalObjects = cameraData.detections ? cameraData.detections.length : 0;
            const fireZones = feedsToRender.filter(f => f.status === 'CRITICAL').length;
            const objEl = document.getElementById('vision-total-objects');
            const fzEl = document.getElementById('vision-fire-zones');
            if (objEl) objEl.textContent = totalObjects;
            if (fzEl) fzEl.textContent = fireZones > 0 ? `${fireZones} Hot-Spot${fireZones > 1 ? 's' : ''}` : 'None';

            // Update Gemma advisory with the most critical feed's reasoning
            const critFeed = feedsToRender.find(f => f.status === 'CRITICAL') || feedsToRender[0];
            const advisory = document.getElementById('vision-gemma-advisory');
            if (advisory && critFeed && critFeed.gemma_vision) {
                advisory.textContent = critFeed.gemma_vision.reasoning || 'Thermal baseline stable.';
            }

            grid.innerHTML = feedsToRender.map((feed, index) => {
                const camId = `CAM_${(index + 1).toString().padStart(2, '0')}`;
                const locStr = feed.floor === 'STAIRS' ? 'STAIRS_B' : (feed.floor === 0 ? 'LOBBY' : `FL_0${feed.floor}`);
                
                // Thermal Cold Background (Deep Purple/Blue)
                let bgClass = 'bg-[#0a0a20]';
                let alertColor = 'text-slate-400';
                let borderGlow = '';
                
                if (feed.status === 'CRITICAL') {
                    borderGlow = 'border-red-500/40 shadow-red-500/20 shadow-lg';
                    alertColor = 'text-red-400';
                } else if (feed.status === 'DANGER') {
                    alertColor = 'text-yellow-400';
                    borderGlow = 'border-yellow-500/30';
                }

                const boxesHtml = feed.detections.map(d => {
                    const left = (d.box[0] / 320) * 100;
                    const top = (d.box[1] / 180) * 100;
                    const width = (d.box[2] / 320) * 100;
                    const height = (d.box[3] / 180) * 100;

                    // Thermal Heat Signature Blobs
                    let thermalBlob = '';
                    if (d.label === 'fire') {
                        thermalBlob = `<div style="position:absolute; top:${top-5}%; left:${left-5}%; width:${width+10}%; height:${height+10}%; background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(255,255,0,0.7) 30%, rgba(255,100,0,0.4) 60%, transparent 80%); filter: blur(12px); mix-blend-mode: screen;"></div>`;
                    } else if (d.label === 'smoke') {
                        thermalBlob = `<div style="position:absolute; top:${top}%; left:${left}%; width:${width}%; height:${height}%; background: radial-gradient(circle, rgba(100,100,255,0.4) 0%, transparent 70%); filter: blur(15px); mix-blend-mode: screen;"></div>`;
                    } else {
                        // Human Heat
                        thermalBlob = `<div style="position:absolute; top:${top}%; left:${left}%; width:${width}%; height:${height}%; background: radial-gradient(circle, rgba(255,165,0,0.6) 0%, rgba(200,0,0,0.3) 60%, transparent 80%); filter: blur(6px); mix-blend-mode: screen;"></div>`;
                    }

                    return `
                        ${thermalBlob}
                        <div class="detection-box" style="top:${top}%;left:${left}%;width:${width}%;height:${height}%;border-color:${d.color}; border-width: 1px; z-index: 10;">
                            <div class="detection-label" style="background:${d.color};color:#000; font-size: 7px;">${d.label.toUpperCase()}</div>
                        </div>
                    `;
                }).join('');

                const gv = feed.gemma_vision || {};
                const bgPatternStyle = `background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 15px 15px;`;

                return `
                    <div class="relative overflow-hidden rounded-xl border ${borderGlow || 'border-white/5'} ${bgClass} transition-all duration-300 hover:border-accent/40 group" style="${bgPatternStyle}">
                        <!-- Camera Feed UI Overlay -->
                        <div class="vision-overlay absolute inset-0 pointer-events-none">
                            ${boxesHtml}
                            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20"></div>
                        </div>

                        <!-- Top Bar -->
                        <div class="absolute top-0 left-0 right-0 flex justify-between items-start p-2 z-20">
                            <div class="flex gap-1 items-center">
                                <span class="px-1 py-0.5 bg-emerald-500 text-[6px] font-black rounded">THERMAL</span>
                                <span class="px-1.5 py-0.5 bg-black/60 text-[7px] font-bold rounded backdrop-blur-sm">${camId} // ${locStr}</span>
                            </div>
                            <div class="text-right">
                                <span class="text-[8px] font-black uppercase ${alertColor} block">${feed.zone_label || 'CLEAR'}</span>
                                <span class="text-[6px] text-slate-500 font-mono">${gv.engine || 'Gemma-Thermal'}</span>
                            </div>
                        </div>

                        <!-- Bottom Reasoning (Gemma) -->
                        <div class="absolute bottom-0 left-0 right-0 p-2 z-20">
                            <div class="bg-black/70 backdrop-blur-sm p-1.5 rounded border-l-2 border-emerald-500">
                                <div class="flex justify-between mb-0.5">
                                    <span class="text-[6px] text-emerald-400 font-black uppercase tracking-wider">Gemma Thermal-Vision</span>
                                    <span class="text-[6px] text-slate-600">${gv.inference_time_ms || '--'}ms</span>
                                </div>
                                <p class="text-[7.5px] text-slate-200 leading-tight line-clamp-2">${gv.reasoning || 'Scanning...'}</p>
                            </div>
                        </div>

                        <!-- Reticle -->
                        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none" style="opacity:0.15;">
                            <div style="width:30px;height:30px;border: 1px solid white; border-radius: 50%; opacity: 0.2;"></div>
                            <div style="position:absolute; top:50%; left:50%; width:10px; height:1px; background:white; transform:translate(-50%,-50%);"></div>
                            <div style="position:absolute; top:50%; left:50%; width:1px; height:10px; background:white; transform:translate(-50%,-50%);"></div>
                        </div>

                        <div class="scanline opacity-10 pointer-events-none"></div>
                    </div>
                `;
            }).join('');
        }

        let fireForecastChart, bottleneckChart;
        function initForecastingCharts() {
            // Fire Spread Chart
            const fireCtx = document.getElementById('fire-forecast-chart').getContext('2d');
            fireForecastChart = new Chart(fireCtx, {
                type: 'line',
                data: {
                    labels: ['+0m', '+5m', '+10m', '+15m', '+20m'],
                    datasets: [{
                        label: 'Probable Breach %',
                        data: [0, 0, 0, 0, 0],
                        borderColor: '#f43f5e',
                        backgroundColor: 'rgba(244, 63, 94, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: { maintainAspectRatio: false }
            });

            // Bottleneck Chart
            const bottleCtx = document.getElementById('bottleneck-chart').getContext('2d');
            bottleneckChart = new Chart(bottleCtx, {
                type: 'bar',
                data: {
                    labels: ['Exit A', 'Stairs L', 'Stairs R', 'Elevator Bank'],
                    datasets: [{
                        label: 'Saturation Level',
                        data: [10, 10, 10, 10],
                        backgroundColor: '#10b981',
                        borderRadius: 4
                    }]
                },
                options: { maintainAspectRatio: false }
            });
        }

        function updateForecasting(assessment) {
            if (!assessment || !fireForecastChart) return;
            
            // Sync guest positions for 2D map
            if (assessment.self_rescuing) {
                let activeRescues = new Set(assessment.self_rescuing);
                guestPositions = guestPositions.filter(g => activeRescues.has(g.room));
                
                assessment.self_rescuing.forEach(roomId => {
                    if (!guestPositions.find(g => g.room === roomId)) {
                        guestPositions.push({ room: roomId, floor: parseInt(roomId.slice(0, -2)) });
                    }
                });
            }
            
            // Simulate future spread from risk scores
            const avgRisk = Object.values(assessment.zone_risk_scores).reduce((a, b) => a + b, 0) / 5;
            const forecastData = [avgRisk, avgRisk*1.2, avgRisk*1.5, avgRisk*1.8, Math.min(100, avgRisk*2.2)];
            
            fireForecastChart.data.datasets[0].data = forecastData;
            fireForecastChart.update();

            if (bottleneckChart && assessment.evac_time) {
                // Dynamic bottlenecking based on blocked exits and estimated time
                const blocked = assessment.evac_time.blocked_exits || 0;
                const time = assessment.evac_time.estimated_time_mins || 10;
                const baseSat = Math.min(95, (time / 20) * 100);
                
                // Exit A, Stairs L, Stairs R, Elevator Bank
                const sat = [
                    Math.min(100, baseSat + (blocked > 0 ? 30 : 0)), // Exit A takes overflow
                    Math.min(100, baseSat + (blocked > 1 ? 40 : 10)), // Stairs L
                    Math.min(100, baseSat + (blocked > 2 ? 50 : 5)),  // Stairs R
                    98 // Elevators are always heavily bottlenecked/disabled
                ];
                bottleneckChart.data.datasets[0].data = sat;
                bottleneckChart.update();
            } else if (bottleneckChart) {
                // If no evac_time yet, keep it at baseline
                bottleneckChart.data.datasets[0].data = [10, 15, 12, 98];
                bottleneckChart.update();
            }

            // Update Heatmap Canvas
            const heatCanvas = document.getElementById('heatmap-replay-canvas');
            if (heatCanvas && assessment.zone_risk_scores) {
                const ctx = heatCanvas.getContext('2d');
                // Set canvas size to match layout
                heatCanvas.width = heatCanvas.clientWidth;
                heatCanvas.height = heatCanvas.clientHeight;
                
                const w = heatCanvas.width;
                const h = heatCanvas.height;
                const floorH = h / 5;
                
                ctx.clearRect(0, 0, w, h);
                
                // Draw floors 4 down to 0 with labels
                for(let f=4; f>=0; f--) {
                    const risk = assessment.zone_risk_scores[f] || 0;
                    const y = (4-f) * floorH;
                    
                    let color = 'rgba(16, 185, 129, 0.05)';
                    if (risk > 70) color = `rgba(244, 63, 94, ${0.1 + risk/100})`;
                    else if (risk > 40) color = `rgba(251, 191, 36, ${0.1 + risk/100})`;
                    else if (risk > 10) color = `rgba(16, 185, 129, ${0.1 + risk/100})`;
                    
                    ctx.fillStyle = color;
                    ctx.fillRect(0, y, w, floorH);
                    
                    ctx.fillStyle = 'rgba(255,255,255,0.05)';
                    ctx.fillRect(10, y + 10, 45, floorH - 20);
                    
                    ctx.fillStyle = risk > 50 ? '#fff' : 'rgba(255,255,255,0.6)';
                    ctx.font = 'bold 10px Inter';
                    ctx.textAlign = 'left';
                    ctx.fillText(f === 0 ? 'GRND' : `FL-0${f}`, 15, y + floorH/2 + 4);
                    
                    ctx.textAlign = 'right';
                    ctx.font = '9px Inter';
                    ctx.fillStyle = risk > 70 ? '#f43f5e' : (risk > 40 ? '#fbbf24' : '#10b981');
                    ctx.fillText(`${risk}% RISK`, w - 15, y + floorH/2 + 4);

                    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
                    ctx.strokeRect(0, y, w, floorH);
                }
            }
        }


        function startTime() {
            setInterval(() => {
                document.getElementById('clock').innerText = new Date().toLocaleTimeString();
            }, 1000);
        }

        function initCharts() {
            // Evacuation Chart
            const evacCtx = document.getElementById('evac-chart').getContext('2d');
            evacChart = new Chart(evacCtx, {
                type: 'line',
                data: {
                    labels: ['T-30m', 'T-20m', 'T-10m', 'T-5m', 'Now'],
                    datasets: [{
                        label: 'Evacuation %',
                        data: [5, 18, 42, 78, 94],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: { 
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b' } }
                    }
                }
            });

            // Performance Chart
            const perfCtx = document.getElementById('performance-chart').getContext('2d');
            performanceChart = new Chart(perfCtx, {
                type: 'bar',
                data: {
                    labels: ['S-01', 'S-02', 'S-03', 'S-04', 'S-05', 'S-06', 'S-07'],
                    datasets: [{
                        label: 'Tasks Completed',
                        data: [12, 19, 15, 8, 22, 14, 18],
                        backgroundColor: '#10b981',
                        borderRadius: 4
                    }]
                },
                options: { 
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b' } }
                    }
                }
            });
        }

        window.onload = () => {
            init();
            twin = new DigitalTwin('digital-twin-container');
            
            // Re-render once layout is settled
            setTimeout(() => {
                if (twin) twin.onResize();
            }, 500);
        };
    