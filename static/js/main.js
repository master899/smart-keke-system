document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    function openSidebar() {
        if (!sidebar || !sidebarOverlay) return;
        sidebar.classList.add("active");
        sidebarOverlay.classList.add("active");
        document.body.classList.add("no-scroll");
    }

    function closeSidebar() {
        if (!sidebar || !sidebarOverlay) return;
        sidebar.classList.remove("active");
        sidebarOverlay.classList.remove("active");
        document.body.classList.remove("no-scroll");
    }

    if (menuToggle) {
        menuToggle.addEventListener("click", openSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", closeSidebar);
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();
        }
    });

    const progressBars = document.querySelectorAll(".map-road-progress[data-progress]");

    progressBars.forEach((bar) => {
        const rawProgress = Number(bar.dataset.progress);
        const safeProgress = Number.isFinite(rawProgress)
            ? Math.min(Math.max(rawProgress, 0), 100)
            : 0;

        bar.style.width = `${safeProgress}%`;
    });
    function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];

    for (const cookie of cookies) {
        const trimmedCookie = cookie.trim();

        if (trimmedCookie.startsWith(`${name}=`)) {
            return decodeURIComponent(trimmedCookie.substring(name.length + 1));
        }
    }

    return null;
}

const driverLocationUpdateInput = document.getElementById("driverLocationUpdateUrl");
const gpsStatus = document.getElementById("gpsStatus");
const driverLatitude = document.getElementById("driverLatitude");
const driverLongitude = document.getElementById("driverLongitude");
const driverLocationUpdated = document.getElementById("driverLocationUpdated");

if (driverLocationUpdateInput) {
    const updateUrl = driverLocationUpdateInput.value;

    if (!navigator.geolocation) {
        if (gpsStatus) gpsStatus.textContent = "GPS not supported";
    } else {
        if (gpsStatus) gpsStatus.textContent = "Requesting permission";

        navigator.geolocation.watchPosition(
            async (position) => {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                if (gpsStatus) gpsStatus.textContent = "Updating";

                try {
                    const response = await fetch(updateUrl, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken"),
                        },
                        body: JSON.stringify({
                            latitude,
                            longitude,
                        }),
                    });

                    const result = await response.json();

                    if (!response.ok || !result.success) {
                        throw new Error(result.message || "Unable to update GPS location.");
                    }

                    if (driverLatitude) driverLatitude.textContent = result.latitude;
                    if (driverLongitude) driverLongitude.textContent = result.longitude;
                    if (driverLocationUpdated) driverLocationUpdated.textContent = result.updated_at;
                    if (gpsStatus) gpsStatus.textContent = "Live";
                } catch (error) {
                    if (gpsStatus) gpsStatus.textContent = "Update failed";
                    console.error(error);
                }
            },
            (error) => {
                if (gpsStatus) {
                    if (error.code === error.PERMISSION_DENIED) {
                        gpsStatus.textContent = "Permission denied";
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        gpsStatus.textContent = "Position unavailable";
                    } else if (error.code === error.TIMEOUT) {
                        gpsStatus.textContent = "GPS timeout";
                    } else {
                        gpsStatus.textContent = "GPS error";
                    }
                }

                console.error("Geolocation error:", error);
            },
            {
                enableHighAccuracy: true,
                maximumAge: 10000,
                timeout: 15000,
            }
        );
    }
}
function initializeLeafletRideMap() {
    const mapElement = document.getElementById("rideLeafletMap");
    const dataElement = document.getElementById("ride-map-data");
    const statusElement = document.getElementById("leafletTrackingStatus");

    if (!mapElement || !dataElement || typeof L === "undefined") {
        return;
    }

    const mapData = JSON.parse(dataElement.textContent);

    if (!mapData.pickup || !mapData.destination) {
        if (statusElement) statusElement.textContent = "Location unavailable";
        return;
    }

    const center = mapData.driver || mapData.pickup;

    const map = L.map(mapElement, {
        zoomControl: true,
        scrollWheelZoom: true,
    }).setView([center.lat, center.lng], 16);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    const driverIcon = L.divIcon({
        className: "leaflet-custom-marker driver-leaflet-marker",
        html: "D",
        iconSize: [38, 38],
        iconAnchor: [19, 19],
    });

    const pickupIcon = L.divIcon({
        className: "leaflet-custom-marker pickup-leaflet-marker",
        html: "P",
        iconSize: [38, 38],
        iconAnchor: [19, 19],
    });

    const destinationIcon = L.divIcon({
        className: "leaflet-custom-marker destination-leaflet-marker",
        html: "X",
        iconSize: [38, 38],
        iconAnchor: [19, 19],
    });

    let driverMarker = null;

    if (mapData.driver) {
        driverMarker = L.marker([mapData.driver.lat, mapData.driver.lng], {
            icon: driverIcon,
        }).addTo(map).bindPopup(`Driver: ${mapData.driverName}`);
    }

    const pickupMarker = L.marker([mapData.pickup.lat, mapData.pickup.lng], {
        icon: pickupIcon,
    }).addTo(map).bindPopup(`Pickup: ${mapData.pickupName}`);

    const destinationMarker = L.marker([mapData.destination.lat, mapData.destination.lng], {
        icon: destinationIcon,
    }).addTo(map).bindPopup(`Destination: ${mapData.destinationName}`);

    const routeLinePoints = [];

    if (mapData.driver) {
        routeLinePoints.push([mapData.driver.lat, mapData.driver.lng]);
    }

    routeLinePoints.push([mapData.pickup.lat, mapData.pickup.lng]);
    routeLinePoints.push([mapData.destination.lat, mapData.destination.lng]);

    let routeLine = L.polyline(routeLinePoints, {
        color: "#0f7a3b",
        weight: 5,
        opacity: 0.75,
        dashArray: "8, 8",
    }).addTo(map);

    const groupItems = [pickupMarker, destinationMarker];

    if (driverMarker) {
        groupItems.push(driverMarker);
    }

    map.fitBounds(L.featureGroup(groupItems).getBounds(), {
        padding: [40, 40],
    });

    if (statusElement) statusElement.textContent = "Live";

    const maximizeMapBtn = document.getElementById("maximizeMapBtn");
    const mapPanel = document.querySelector(".leaflet-map-panel");

    function refreshMapSize() {
        setTimeout(() => {
            map.invalidateSize();
        }, 250);
    }

    function openMapFullscreen() {
        if (!mapPanel) return;

        mapPanel.classList.add("map-fullscreen-mode");
        document.body.classList.add("no-scroll");

        if (maximizeMapBtn) {
            maximizeMapBtn.textContent = "Minimize";
        }

        refreshMapSize();
    }

    function closeMapFullscreen() {
        if (!mapPanel) return;

        mapPanel.classList.remove("map-fullscreen-mode");
        document.body.classList.remove("no-scroll");

        if (maximizeMapBtn) {
            maximizeMapBtn.textContent = "Maximize";
        }

        refreshMapSize();
    }

    if (maximizeMapBtn && mapPanel) {
        maximizeMapBtn.addEventListener("click", () => {
            if (mapPanel.classList.contains("map-fullscreen-mode")) {
                closeMapFullscreen();
            } else {
                openMapFullscreen();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && mapPanel.classList.contains("map-fullscreen-mode")) {
                closeMapFullscreen();
            }
        });
    }

    async function refreshDriverLocation() {
        try {
            const response = await fetch(mapData.trackingUrl, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "Tracking update failed.");
            }

            if (result.driver) {
                const newPosition = [result.driver.lat, result.driver.lng];

                if (!driverMarker) {
                    driverMarker = L.marker(newPosition, {
                        icon: driverIcon,
                    }).addTo(map).bindPopup(`Driver: ${mapData.driverName}`);
                } else {
                    driverMarker.setLatLng(newPosition);
                }

                map.removeLayer(routeLine);

                const updatedRouteLinePoints = [
                    newPosition,
                    [result.pickup.lat, result.pickup.lng],
                    [result.destination.lat, result.destination.lng],
                ];

                routeLine = L.polyline(updatedRouteLinePoints, {
                    color: "#0f7a3b",
                    weight: 5,
                    opacity: 0.75,
                    dashArray: "8, 8",
                }).addTo(map);

                if (statusElement) {
                    statusElement.textContent = `Live • ${result.rideStatusDisplay}`;
                }
            }
        } catch (error) {
            if (statusElement) statusElement.textContent = "Tracking delayed";
            console.error(error);
        }
    }

    refreshDriverLocation();
    setInterval(refreshDriverLocation, 10000);
}

initializeLeafletRideMap();
});