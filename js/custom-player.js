var player = videojs('curr-video', {
    plugins: {
        hotkeys: {
            volumeStep: 0.1,
            seekStep: 5,
            enableModifiersForNumbers: false,
        },
    },
});
player.fluid(true);
player.aspectRatio('16:9');

// Get video filename from data attribute
var videoElement = document.getElementById('curr-video');
var videoFilename = videoElement ? videoElement.getAttribute('data-video') : null;

// Thumbnail preview functionality
player.ready(function() {
    var progressControl = player.controlBar.progressControl;
    var seekBar = progressControl ? progressControl.seekBar : null;
    
    if (!seekBar || !videoFilename) {
        return;
    }
    
    // Create thumbnail preview element
    var thumbnailPreview = document.createElement('div');
    thumbnailPreview.id = 'thumbnail-preview';
    thumbnailPreview.style.cssText = 'position: absolute; display: none; z-index: 1000; pointer-events: none; background: #000; border: 2px solid #fff; border-radius: 4px; padding: 2px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);';
    document.body.appendChild(thumbnailPreview);
    
    var thumbnailImg = document.createElement('img');
    thumbnailImg.style.cssText = 'display: block; max-width: 320px; max-height: 180px;';
    thumbnailPreview.appendChild(thumbnailImg);
    
    var thumbnailTime = document.createElement('div');
    thumbnailTime.style.cssText = 'color: #fff; text-align: center; font-size: 12px; padding: 2px 4px; background: rgba(0,0,0,0.7); border-radius: 2px; margin-top: 2px;';
    thumbnailPreview.appendChild(thumbnailTime);
    
    var currentThumbnailRequest = null;
    var thumbnailCache = {};
    var debounceTimer = null;
    
    function formatTime(seconds) {
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        var s = Math.floor(seconds % 60);
        if (h > 0) {
            return h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }
        return m + ':' + (s < 10 ? '0' : '') + s;
    }
    
    function loadThumbnail(time) {
        // Round time to nearest 0.5 seconds for caching
        var roundedTime = Math.round(time * 2) / 2;
        
        // Check cache first
        if (thumbnailCache[roundedTime]) {
            thumbnailImg.src = thumbnailCache[roundedTime];
            thumbnailTime.textContent = formatTime(roundedTime);
            return;
        }
        
        // Cancel previous request if still pending
        if (currentThumbnailRequest) {
            currentThumbnailRequest.abort();
        }
        
        // Create new request
        var xhr = new XMLHttpRequest();
        currentThumbnailRequest = xhr;
        
        xhr.open('GET', '/thumbnail?video=' + encodeURIComponent(videoFilename) + '&time=' + roundedTime, true);
        xhr.responseType = 'blob';
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var blob = xhr.response;
                var url = URL.createObjectURL(blob);
                thumbnailCache[roundedTime] = url;
                thumbnailImg.src = url;
                thumbnailTime.textContent = formatTime(roundedTime);
            } else {
                thumbnailPreview.style.display = 'none';
            }
            currentThumbnailRequest = null;
        };
        
        xhr.onerror = function() {
            thumbnailPreview.style.display = 'none';
            currentThumbnailRequest = null;
        };
        
        xhr.send();
    }
    
    function showThumbnail(e) {
        if (!player.duration()) {
            return;
        }
        
        var seekBarEl = seekBar.el();
        var rect = seekBarEl.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var percent = Math.max(0, Math.min(1, x / rect.width));
        var time = percent * player.duration();
        
        // Debounce thumbnail requests
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function() {
            loadThumbnail(time);
        }, 50);
        
        // Position and show preview
        thumbnailPreview.style.display = 'block';
        var previewRect = thumbnailPreview.getBoundingClientRect();
        var left = e.clientX - previewRect.width / 2;
        var top = rect.top - previewRect.height - 10;
        
        // Keep preview within viewport
        if (left < 10) left = 10;
        if (left + previewRect.width > window.innerWidth - 10) {
            left = window.innerWidth - previewRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10;
        }
        
        thumbnailPreview.style.left = left + 'px';
        thumbnailPreview.style.top = top + 'px';
    }
    
    function hideThumbnail() {
        thumbnailPreview.style.display = 'none';
        clearTimeout(debounceTimer);
        if (currentThumbnailRequest) {
            currentThumbnailRequest.abort();
            currentThumbnailRequest = null;
        }
    }
    
    // Add event listeners to seek bar
    seekBar.on('mousemove', showThumbnail);
    seekBar.on('mouseleave', hideThumbnail);
    
    // Also handle mouseout on the progress control
    progressControl.on('mouseleave', hideThumbnail);
});

