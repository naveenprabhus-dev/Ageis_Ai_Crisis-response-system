/**
 * Aegis AI — Digital Twin 3D Engine (v3.0)
 * Architectural model of Ground + 4 Floor Hotel.
 * Layout: 10 rooms per floor, central corridor, dual stairwells.
 */

class DigitalTwin {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        console.log("DigitalTwin initializing on:", containerId);
        if (!this.container) return;
        
        this.scene = new THREE.Scene();
        this.scene.background = null; // Transparent for overlay
        
        const width = this.container.clientWidth || 800;
        const height = this.container.clientHeight || 600;
        
        this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
        this.camera.position.set(100, 60, 100); 
        this.camera.lookAt(0, 20, 0); 
        
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        const controlsClass = THREE.OrbitControls || window.OrbitControls;
        if (controlsClass) {
            this.controls = new controlsClass(this.camera, this.renderer.domElement);
            this.controls.target.set(0, 20, 0); 
            this.controls.enableDamping = true;
        }

        this.rooms = {}; 
        this.floors = []; 
        this.staffMeshes = {}; 
        
        // Raycasting & Hover
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredRoom = null;
        this.latestAssessment = null;
        
        this.tt = document.getElementById('twin-tooltip');
        this.container.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.container.addEventListener('mouseleave', () => this.hideTooltip());
        
        this.initLights();
        this.buildHotel();
        this.animate();
    }

    onMouseMove(event) {
        if (!this.container || !this.raycaster) return;
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        // Intersect Rooms
        const roomIntersects = this.raycaster.intersectObjects(Object.values(this.rooms), false);
        
        // Intersect Staff Dots
        const staffMeshObjects = Object.values(this.staffMeshes).map(s => s.mesh);
        const staffIntersects = this.raycaster.intersectObjects(staffMeshObjects, false);

        if (staffIntersects.length > 0) {
            const hit = staffIntersects[0].object;
            const staffId = Object.keys(this.staffMeshes).find(k => this.staffMeshes[k].mesh === hit);
            if (staffId) {
                this.showStaffTooltip(staffId, event.clientX, event.clientY);
                return;
            }
        }

        if (roomIntersects.length > 0) {
            const hit = roomIntersects[0].object;
            const roomId = Object.keys(this.rooms).find(k => this.rooms[k] === hit);
            if (roomId) {
                if (this.hoveredRoom !== roomId) {
                    this.hoveredRoom = roomId;
                    this.showTooltip(roomId, event.clientX, event.clientY);
                } else {
                    this.moveTooltip(event.clientX, event.clientY);
                }
            }
        } else {
            if (this.hoveredRoom) {
                this.hoveredRoom = null;
                this.hideTooltip();
            }
        }
    }

    showStaffTooltip(staffId, x, y) {
        if (!this.tt) return;
        this.tt.classList.remove('hidden');
        this.moveTooltip(x, y);

        const assignments = this.latestAssessment ? this.latestAssessment.staff_assignments : null;
        const info = assignments && assignments[staffId] ? assignments[staffId] : null;

        document.getElementById('tt-room').innerText = `STAFF UNIT`;
        document.getElementById('tt-floor').innerText = staffId;
        
        document.getElementById('tt-guest-name').innerText = info ? info.staff_name : staffId;
        document.getElementById('tt-guest-dot').className = 'w-2 h-2 rounded-full bg-yellow-400';
        document.getElementById('tt-guest-vuln').classList.add('hidden');
        
        const eStatus = document.getElementById('tt-evac-status');
        eStatus.innerText = info ? info.status : 'IDLE / PATROL';
        eStatus.className = 'px-2 py-1 border rounded text-[9px] font-bold uppercase bg-yellow-900/50 border-yellow-500/50 text-yellow-500';

        document.getElementById('tt-staff-id').innerText = 'Operations Unit';
        document.getElementById('tt-staff-dot').className = 'w-2 h-2 rounded-full bg-yellow-500';
        document.getElementById('tt-staff-eta').classList.add('hidden');
    }

    showTooltip(roomId, x, y) {
        if (!this.tt) return;
        this.tt.classList.remove('hidden');
        this.moveTooltip(x, y);

        const floor = parseInt(roomId.slice(0, -2));
        document.getElementById('tt-room').innerText = `ROOM ${roomId}`;
        document.getElementById('tt-floor').innerText = floor === 0 ? 'GRND' : `FLOOR ${floor}`;

        // Fetch Guest Data
        const hotelData = this.latestAssessment ? this.latestAssessment.hotel_data : null;
        const guestData = hotelData && hotelData.guests ? hotelData.guests[roomId] : null;
        const isSelfRescuing = this.latestAssessment && this.latestAssessment.self_rescuing && this.latestAssessment.self_rescuing.some(r => r.room === roomId);

        const gName = document.getElementById('tt-guest-name');
        const gDot = document.getElementById('tt-guest-dot');
        const gVuln = document.getElementById('tt-guest-vuln');
        const eStatus = document.getElementById('tt-evac-status');

        if (guestData) {
            gName.innerText = guestData.name || 'Unknown Guest';
            gDot.className = `w-2 h-2 rounded-full ${guestData.status === 'EVACUATING' || isSelfRescuing ? 'bg-yellow-400' : 'bg-green-400'}`;
            if (guestData.is_vulnerable) {
                gVuln.classList.remove('hidden');
                gVuln.innerText = `⚠️ Vulnerable (Age: ${guestData.age})`;
            } else {
                gVuln.classList.add('hidden');
            }
            
            if (isSelfRescuing) {
                eStatus.innerText = 'SELF-RESCUE ACTIVE (AI GUIDED)';
                eStatus.className = 'px-2 py-1 border rounded text-[9px] font-bold uppercase bg-blue-900/50 border-blue-500/50 text-blue-400';
            } else {
                eStatus.innerText = guestData.status === 'EVACUATING' ? 'EVACUATING' : 'IN ROOM';
                eStatus.className = `px-2 py-1 border rounded text-[9px] font-bold uppercase ${guestData.status === 'EVACUATING' ? 'bg-yellow-900/50 border-yellow-500/50 text-yellow-500' : 'bg-green-900/50 border-green-500/50 text-green-500'}`;
            }
        } else {
            gName.innerText = 'No Guest Registered';
            gDot.className = 'w-2 h-2 rounded-full bg-slate-600';
            gVuln.classList.add('hidden');
            eStatus.innerText = 'Monitoring';
            eStatus.className = 'px-2 py-1 bg-black/50 border border-white/10 rounded text-[9px] font-bold uppercase text-slate-400';
        }

        // Fetch Staff Assignment
        const assignments = this.latestAssessment ? this.latestAssessment.staff_assignments : null;
        let assignedStaff = null;
        if (assignments) {
            for (const [sid, data] of Object.entries(assignments)) {
                if (data.room === roomId) {
                    assignedStaff = { id: sid, ...data };
                    break;
                }
            }
        }

        const sId = document.getElementById('tt-staff-id');
        const sDot = document.getElementById('tt-staff-dot');
        const sEta = document.getElementById('tt-staff-eta');

        if (assignedStaff) {
            sId.innerText = assignedStaff.staff_name || assignedStaff.id;
            sDot.className = `w-2 h-2 rounded-full ${assignedStaff.status === 'CRITICAL' ? 'bg-red-500' : 'bg-accent'}`;
            sEta.innerText = `ETA: ${assignedStaff.eta}m`;
            sEta.classList.remove('hidden');
        } else {
            sId.innerText = 'Unassigned';
            sDot.className = 'w-2 h-2 rounded-full bg-slate-600';
            sEta.classList.add('hidden');
        }
    }

    moveTooltip(x, y) {
        if (!this.tt) return;
        const rect = this.container.getBoundingClientRect();
        this.tt.style.left = (x - rect.left + 15) + 'px';
        this.tt.style.top = (y - rect.top + 15) + 'px';
    }

    hideTooltip() {
        if (this.tt) this.tt.classList.add('hidden');
    }

    initLights() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.2); // Stronger ambient
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x10b981, 2, 500); // Neon green glow
        pointLight.position.set(50, 100, 50);
        this.scene.add(pointLight);

        const fillLight = new THREE.PointLight(0xffffff, 1, 300);
        fillLight.position.set(-50, 50, -50);
        this.scene.add(fillLight);
    }

    buildHotel() {
        const floorHeight = 10;
        const roomSize = 8;
        const corridorWidth = 6;
        const floorWidth = (5 * roomSize);
        const floorDepth = (2 * roomSize) + corridorWidth;

        for (let f = 0; f < 5; f++) {
            const floorGroup = new THREE.Group();
            floorGroup.position.y = f * floorHeight;
            
            // Floor Plate
            const plateGeom = new THREE.BoxGeometry(floorWidth + 10, 0.5, floorDepth + 4);
            const plateMat = new THREE.MeshBasicMaterial({ 
                color: 0x1e293b, 
                transparent: true, 
                opacity: 0.3,
            });
            const plate = new THREE.Mesh(plateGeom, plateMat);
            floorGroup.add(plate);

            // Central Corridor
            const corrGeom = new THREE.PlaneGeometry(floorWidth, corridorWidth);
            const corrMat = new THREE.MeshBasicMaterial({ color: 0x334155, side: THREE.DoubleSide });
            const corr = new THREE.Mesh(corrGeom, corrMat);
            corr.rotation.x = -Math.PI / 2;
            corr.position.y = 0.3;
            floorGroup.add(corr);

            // Rooms (5 on side A, 5 on side B)
            for (let r = 1; r <= 10; r++) {
                const isSideA = r <= 5;
                const roomIdx = isSideA ? r - 1 : r - 6;
                const roomId = `${f}${r < 10 ? '0'+r : r}`;
                
                const roomGeom = new THREE.BoxGeometry(roomSize - 1, 6, roomSize - 1);
                const roomMat = new THREE.MeshBasicMaterial({ 
                    color: 0x10b981, 
                    transparent: true, 
                    opacity: 0.7, // Higher opacity
                });
                const room = new THREE.Mesh(roomGeom, roomMat);
                
                // Position logic: centered along corridor
                room.position.x = -(floorWidth/2) + (roomIdx * roomSize) + (roomSize/2);
                room.position.z = isSideA ? -(roomSize + corridorWidth/2) + (roomSize/2) : (corridorWidth/2) + (roomSize/2);
                room.position.y = 3.3;
                
                // Wireframe for edges
                const edges = new THREE.EdgesGeometry(roomGeom);
                const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.8 }));
                room.add(line);

                this.rooms[roomId] = room;
                floorGroup.add(room);
                
                // Ground Floor Labels
                if (f === 0) {
                    let label = "";
                    if (r === 1) label = "RECEPTION";
                    if (r === 2) label = "LOUNGE";
                    if (r === 3) label = "DINING L";
                    if (r === 4) label = "DINING R";
                    if (r === 5) label = "KITCHEN";
                    if (label) this.addLabel(room, label);
                } else {
                    this.addLabel(room, roomId);
                }
            }

            this.floors.push(floorGroup);
            this.scene.add(floorGroup);
        }

        // STAIRWELLS (Left and Right)
        this.addVerticalFeature(-(floorWidth/2 + 4), 0, "STAIRS L", 0x6366f1);
        this.addVerticalFeature((floorWidth/2 + 4), 0, "STAIRS R", 0x6366f1);
        
        // ELEVATOR (Center)
        this.addVerticalFeature(0, 0, "ELEVATOR", 0xfacc15);
    }

    addVerticalFeature(x, z, label, color) {
        const geom = new THREE.BoxGeometry(4, 50, 4);
        const mat = new THREE.MeshPhongMaterial({ color: color, transparent: true, opacity: 0.1 });
        const mesh = new THREE.Mesh(geom, mat);
        mesh.position.set(x, 20, z);
        this.scene.add(mesh);
        
        const edges = new THREE.EdgesGeometry(geom);
        const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.4 }));
        mesh.add(line);
        this.addLabel(mesh, label, 26);
    }

    addLabel(parent, text, yOffset = 4) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 512;
        canvas.height = 128;
        ctx.fillStyle = 'white';
        ctx.font = 'Bold 48px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(text, 256, 80);
        
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(8, 2, 1);
        sprite.position.y = yOffset;
        parent.add(sprite);
    }

    updateState(assessment) {
        if (!assessment) return;
        this.latestAssessment = assessment;
        const highAlertZones = assessment.high_alert_zones || [];
        const mediumAlertZones = assessment.medium_alert_zones || [];
        const hotelData = assessment.hotel_data ? assessment.hotel_data.hotel : {};

        for (let roomId in this.rooms) {
            const mesh = this.rooms[roomId];
            const floor = parseInt(roomId.slice(0, -2));
            const roomInfo = hotelData[floor] ? hotelData[floor][roomId] : null;
            const isStaticHighAlert = roomInfo && roomInfo.is_high_alert;
            
            const fireZones = assessment.fire_spread ? assessment.fire_spread.etas : {};
            const actualFireZones = assessment.fire_spread && assessment.fire_spread.actual_fire_zones ? assessment.fire_spread.actual_fire_zones : [];
            const isRoomOnFire = actualFireZones.includes(roomId);
            const isRoomThreatened = fireZones[roomId] !== undefined && fireZones[roomId] < 15 && !isRoomOnFire;
            
            let color = 0x22c55e; // Default Safe (Green)
            let opacity = 0.15;

            mesh.userData = {
                isRoomOnFire: isRoomOnFire,
                isStaticHighAlert: isStaticHighAlert && !isRoomOnFire
            };

            if (isRoomOnFire) {
                color = 0xff0000; // Fire (Red)
                opacity = 0.9;
            } else if (isRoomThreatened) {
                color = 0xf97316; // Threatened (Orange)
                opacity = 0.7;
            } else if (highAlertZones.includes(roomId)) {
                color = 0xf59e0b; // High Alert (Amber)
                opacity = 0.6;
            } else if (mediumAlertZones.includes(roomId)) {
                color = 0xfcd34d; // Medium Alert (Yellow)
                opacity = 0.4;
            } else if (isStaticHighAlert) {
                color = 0xfacc15; 
                opacity = 0.35;
            }

            // Force color update
            mesh.material.color.setHex(color);
            mesh.material.opacity = opacity;
            mesh.material.needsUpdate = true;
        }

        this.updateStaffMeshes(assessment.staff_assignments, assessment.staff_locations);
        this.updateGuestMeshes(assessment.self_rescuing);
        
        // Render one frame to reflect changes immediately
        this.renderer.render(this.scene, this.camera);
    }

    updateStaffMeshes(assignments, locations) {
        if (!this.staffMat) {
            this.staffMat = new THREE.MeshBasicMaterial({ color: 0xfacc15 }); // YELLOW DOTS
            this.staffGeom = new THREE.SphereGeometry(1.0, 16, 16);
        }

        const allStaffIds = ["S-01", "S-02", "S-03", "S-04", "S-05", "S-06", "S-07", "S-08", "S-09", "S-10"];
        const staffNames = {
            "S-01": "S-01", "S-02": "S-02", "S-03": "S-03", "S-04": "S-04",
            "S-05": "S-05", "S-06": "S-06", "S-07": "S-07", "S-08": "S-08",
            "S-09": "S-09", "S-10": "S-10"
        };

        allStaffIds.forEach(sid => {
            this._ensureStaffMesh(sid, staffNames[sid]);
            
            // Check if they have an active assignment
            const assignment = assignments ? assignments[sid] : null;
            const location = locations ? locations[sid] : null;

            if (assignment && assignment.room && this.rooms[assignment.room]) {
                this._setStaffTarget(sid, assignment.room);
            } else if (location && location.room && this.rooms[location.room]) {
                this._setStaffTarget(sid, location.room);
            } else {
                // Sentinel position (Idle)
                const floorMap = {
                    "S-01": 0, "S-02": 0, "S-03": 0, // 3 on Ground
                    "S-04": 1, "S-05": 1,           // 2 on 1st
                    "S-06": 2,                      // 1 on 2nd
                    "S-07": 3, "S-08": 3, "S-09": 3, // 3 on 3rd
                    "S-10": 4                       // 1 on 4th
                };
                const floor = floorMap[sid] !== undefined ? floorMap[sid] : 0;
                const num = parseInt(sid.split('-')[1]);
                const isLeft = num % 2 !== 0;
                
                const randomOffset = (Math.random() - 0.5) * 10;
                const targetPos = new THREE.Vector3(
                    (isLeft ? -20 : 20) + randomOffset, // Near Stairwell with random offset
                    (floor * 10) + 1, // Floor height
                    0 // Corridor center (STRICTLY IN CORRIDOR)
                );
                this.staffMeshes[sid].targetPos = targetPos;
            }
        });

        // CLEANUP: Remove staff that are no longer in the ID pool (e.g. ALPHA/BRAVO/etc)
        for (const sid in this.staffMeshes) {
            if (!allStaffIds.includes(sid)) {
                this.scene.remove(this.staffMeshes[sid].mesh);
                delete this.staffMeshes[sid];
            }
        }
    }

    _ensureStaffMesh(sid, name = "") {
        if (!this.staffMeshes[sid]) {
            const mesh = new THREE.Mesh(this.staffGeom, this.staffMat);
            mesh.position.set(0, 5, 0); 
            this.scene.add(mesh);
            this.staffMeshes[sid] = { mesh: mesh, sid: sid };
            
            // Add Label
            this.addLabel(mesh, name || sid, 2.5);
        }
    }

    _setStaffTarget(sid, roomId) {
        const staff = this.staffMeshes[sid];
        const targetMesh = this.rooms[roomId];
        const targetPos = new THREE.Vector3();
        targetMesh.getWorldPosition(targetPos);
        targetPos.y += 1;
        targetPos.z = 0; // Center corridor (STRICTLY NOT INSIDE ROOMS)
        staff.targetPos = targetPos;
    }

    updateGuestMeshes(selfRescuing) {
        if (!this.guestMat) {
            this.guestMat = new THREE.MeshBasicMaterial({ color: 0xffffff }); // WHITE DOTS
            this.guestGeom = new THREE.SphereGeometry(0.8, 16, 16);
        }

        const hotelData = this.latestAssessment ? this.latestAssessment.hotel_data : null;
        const allGuests = hotelData && hotelData.guests ? hotelData.guests : {};
        if (!this.guestMeshes) this.guestMeshes = {};
        const activeGuests = new Set();

        Object.entries(allGuests).forEach(([roomId, guest]) => {
            if (!this.rooms[roomId]) return;
            const gid = `G-${roomId}`;
            activeGuests.add(gid);
            
            if (!this.guestMeshes[gid]) {
                const mesh = new THREE.Mesh(this.guestGeom, this.guestMat);
                const roomMesh = this.rooms[roomId];
                const startPos = new THREE.Vector3();
                roomMesh.getWorldPosition(startPos);
                mesh.position.copy(startPos);
                this.scene.add(mesh);
                this.guestMeshes[gid] = { mesh: mesh, gid: gid };
            }
            
            const roomMesh = this.rooms[roomId];
            const targetPos = new THREE.Vector3();
            roomMesh.getWorldPosition(targetPos);
            
            // Movement Logic
            const isEvacuating = guest.status === "EVACUATING" || 
                                 (this.latestAssessment && this.latestAssessment.self_rescuing && 
                                  this.latestAssessment.self_rescuing.some(r => r.room === roomId));

            if (isEvacuating) {
                // MOVE TOWARDS NEAREST STAIRWELL
                const floor = parseInt(roomId.slice(0, -2));
                const roomNum = parseInt(roomId.slice(1));
                const targetX = roomNum <= 5 ? -25 : 25; // Left or Right Stairwell
                targetPos.set(targetX, (floor * 10) + 1, 0); // Position in central corridor
                this.guestMeshes[gid].mesh.visible = true;
                this.guestMeshes[gid].mesh.material.color.setHex(0x60a5fa); // Blue for evacuating
            } else {
                targetPos.y += 0.5; // Inside Room (Centered)
                this.guestMeshes[gid].mesh.visible = true;
                this.guestMeshes[gid].mesh.material.color.setHex(0xffffff); // White for stationary
            }
            
            this.guestMeshes[gid].targetPos = targetPos;
        });
        
        for (const gid in this.guestMeshes) {
            if (!activeGuests.has(gid)) {
                this.scene.remove(this.guestMeshes[gid].mesh);
                delete this.guestMeshes[gid];
            }
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        if (this.controls) this.controls.update();

        const time = Date.now();

        for (let roomId in this.rooms) {
            const mesh = this.rooms[roomId];
            if (mesh.userData.isRoomOnFire) {
                mesh.scale.setScalar(1 + Math.sin(time * 0.01) * 0.05);
                mesh.material.opacity = 0.6 + Math.sin(time * 0.01) * 0.3; // Rapid pulse
            } else if (mesh.userData.isStaticHighAlert) {
                mesh.scale.setScalar(1 + Math.sin(time * 0.002) * 0.02);
                mesh.material.opacity = 0.4 + Math.sin(time * 0.002) * 0.2; // Slow pulse
            } else {
                mesh.scale.setScalar(1);
            }
        }

        // Smoothly move staff units towards their target assignments
        const lerpFactor = 0.05; // Smoother and faster
        for (const sid in this.staffMeshes) {
            const staff = this.staffMeshes[sid];
            if (staff.targetPos) {
                staff.mesh.position.lerp(staff.targetPos, lerpFactor);
            }
        }

        if (this.guestMeshes) {
            for (const gid in this.guestMeshes) {
                const guest = this.guestMeshes[gid];
                if (guest.targetPos) {
                    guest.mesh.position.lerp(guest.targetPos, lerpFactor);
                }
            }
        }

        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        if (!this.container) return;
        const width = this.container.clientWidth || 800;
        const height = this.container.clientHeight || 600;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
}
