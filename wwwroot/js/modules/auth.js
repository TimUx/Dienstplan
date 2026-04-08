import { API_BASE, escapeHtml, fetchCsrfToken, getCsrfToken, showToast } from './utils.js';

// Authentication state
export let currentUser = null;
export let userRoles = [];

export async function checkAuthenticationStatus() {
    await fetchCsrfToken();
    try {
        const response = await fetch(`${API_BASE}/auth/current-user`, {
            credentials: 'include'
        });

        if (response.ok) {
            const user = await response.json();
            currentUser = user;
            userRoles = user.roles || [];
            updateUIForAuthenticatedUser(user);
        } else {
            updateUIForAnonymousUser();
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
        updateUIForAnonymousUser();
    }

    // Load initial view — uses window.loadSchedule to avoid circular imports
    if (window.loadSchedule) {
        window.loadSchedule();
    }
}

export function updateUIForAuthenticatedUser(user) {
    document.getElementById('user-info').style.display = 'flex';
    document.getElementById('login-prompt').style.display = 'none';
    document.getElementById('user-name').textContent = user.fullName || user.email;

    const isAdmin = userRoles.includes('Admin');
    const isDisponent = userRoles.includes('Disponent');

    document.querySelectorAll('.admin-only').forEach(el => {
        if (isAdmin || isDisponent) {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });

    if (isAdmin) {
        document.body.classList.add('admin');
        document.getElementById('nav-admin').style.display = 'inline-block';
        document.getElementById('nav-management').style.display = 'inline-block';
        document.getElementById('nav-statistics').style.display = 'inline-block';
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
        const vacationYearApprovalsTab = document.getElementById('tab-vacation-year-approvals');
        if (vacationYearApprovalsTab) {
            vacationYearApprovalsTab.style.display = '';
        }
    } else if (isDisponent) {
        document.body.classList.add('disponent');
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    } else {
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    }

    if (isAdmin || isDisponent) {
        startNotificationPolling();
    }
}

export function updateUIForAnonymousUser() {
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('login-prompt').style.display = 'block';
    currentUser = null;
    userRoles = [];
    document.body.classList.remove('admin', 'disponent');
    document.getElementById('nav-admin').style.display = 'none';
    document.getElementById('nav-absences').style.display = 'none';
    document.getElementById('nav-shiftexchange').style.display = 'none';

    stopNotificationPolling();
}

export function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
    document.getElementById('loginError').style.display = 'none';
}

export function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').style.display = 'none';
}

export async function login(event) {
    event.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;

    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken() || ''
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                password: password,
                rememberMe: rememberMe
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            currentUser = data.user;
            userRoles = data.user.roles || [];
            updateUIForAuthenticatedUser(data.user);
            closeLoginModal();
            if (data.requiresPasswordChange) {
                showChangePasswordModal();
                showToast('Bitte ändern Sie Ihr Passwort.', 'warning', 0);
                return;
            }
            if (window.showView) {
                window.showView('schedule');
            }
        } else {
            errorDiv.textContent = data.error || 'Anmeldung fehlgeschlagen';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Netzwerkfehler: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

export async function logout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            headers: {
                'X-CSRF-Token': getCsrfToken() || ''
            },
            credentials: 'include'
        });

        await fetchCsrfToken();

        updateUIForAnonymousUser();
        if (window.showView) {
            window.showView('schedule');
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

export function isAuthenticated() {
    return currentUser !== null;
}

export function hasRole(role) {
    return userRoles.includes(role);
}

export function canEditEmployees() {
    return hasRole('Admin') || hasRole('Disponent');
}

export function canPlanShifts() {
    return hasRole('Admin') || hasRole('Disponent');
}

/**
 * Check if current user is admin (uses sessionStorage fallback)
 */
export function isAdmin() {
    const storedUser = sessionStorage.getItem('currentUser');
    if (!storedUser) return false;

    try {
        const user = JSON.parse(storedUser);
        return user.roles && user.roles.includes('Admin');
    } catch {
        return false;
    }
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

export let currentNotificationFilter = 'unread';

export const NOTIFICATION_POLL_INTERVAL_MS = 60000;
let notificationPollInterval = null;

export async function loadNotificationCount() {
    try {
        const response = await fetch(`${API_BASE}/notifications/count`, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            const badge = document.getElementById('notification-badge');

            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading notification count:', error);
    }
}

export function showNotificationModal() {
    document.getElementById('notificationModal').style.display = 'block';
    currentNotificationFilter = 'unread';
    loadNotifications('unread');
}

export function closeNotificationModal() {
    document.getElementById('notificationModal').style.display = 'none';
}

export function filterNotifications(filter) {
    currentNotificationFilter = filter;

    document.getElementById('filter-all').classList.toggle('active', filter === 'all');
    document.getElementById('filter-unread').classList.toggle('active', filter === 'unread');

    loadNotifications(filter);
}

export async function loadNotifications(filter = 'unread') {
    const listContainer = document.getElementById('notification-list');
    listContainer.innerHTML = '<p class="loading">Lade Benachrichtigungen...</p>';

    try {
        const unreadOnly = filter === 'unread';
        const response = await fetch(`${API_BASE}/notifications?unreadOnly=${unreadOnly}&limit=50`, {
            credentials: 'include'
        });

        if (response.ok) {
            const notifications = await response.json();
            displayNotifications(notifications);
        } else if (response.status === 401) {
            listContainer.innerHTML = '<p class="notification-empty">Bitte melden Sie sich an.</p>';
        } else if (response.status === 403) {
            listContainer.innerHTML = '<p class="notification-empty">Keine Berechtigung.</p>';
        } else {
            listContainer.innerHTML = '<p class="notification-empty">Fehler beim Laden der Benachrichtigungen.</p>';
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        listContainer.innerHTML = '<p class="notification-empty">Fehler beim Laden der Benachrichtigungen.</p>';
    }
}

export function displayNotifications(notifications) {
    const listContainer = document.getElementById('notification-list');

    if (notifications.length === 0) {
        listContainer.innerHTML = `
            <div class="notification-empty">
                <div class="notification-empty-icon">✅</div>
                <p>Keine Benachrichtigungen vorhanden.</p>
            </div>
        `;
        return;
    }

    let html = '';
    notifications.forEach(notification => {
        const unreadClass = notification.isRead ? '' : 'unread';
        const severityClass = `severity-${notification.severity}`;
        const date = new Date(notification.createdAt).toLocaleString('de-DE');

        html += `
            <div class="notification-item ${unreadClass} ${severityClass}">
                <div class="notification-item-header">
                    <h3 class="notification-item-title">${escapeHtml(notification.title)}</h3>
                    <span class="notification-severity ${notification.severity}">${notification.severity}</span>
                </div>
                <div class="notification-item-message">${escapeHtml(notification.message)}</div>
                <div class="notification-item-meta">
                    <span class="notification-item-date">${date}</span>
                    <div class="notification-item-actions">
                        ${!notification.isRead ? `
                            <button class="btn-mark-read" onclick="markNotificationRead(${notification.id})">
                                ✓ Als gelesen markieren
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });

    listContainer.innerHTML = html;
}

export async function markNotificationRead(notificationId) {
    try {
        const response = await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            loadNotifications(currentNotificationFilter);
            loadNotificationCount();
        } else {
            alert('Fehler beim Markieren der Benachrichtigung.');
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
        alert('Fehler beim Markieren der Benachrichtigung.');
    }
}

export async function markAllNotificationsRead() {
    if (!confirm('Möchten Sie wirklich alle Benachrichtigungen als gelesen markieren?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/notifications/mark-all-read`, {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            const result = await response.json();
            alert(`${result.count} Benachrichtigung${result.count !== 1 ? 'en' : ''} als gelesen markiert.`);
            loadNotifications(currentNotificationFilter);
            loadNotificationCount();
        } else {
            alert('Fehler beim Markieren der Benachrichtigungen.');
        }
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        alert('Fehler beim Markieren der Benachrichtigungen.');
    }
}

export function startNotificationPolling() {
    if (notificationPollInterval) {
        clearInterval(notificationPollInterval);
    }

    loadNotificationCount();

    notificationPollInterval = setInterval(() => {
        loadNotificationCount();
    }, NOTIFICATION_POLL_INTERVAL_MS);
}

export function stopNotificationPolling() {
    if (notificationPollInterval) {
        clearInterval(notificationPollInterval);
        notificationPollInterval = null;
    }
}

// ============================================================================
// PASSWORD MANAGEMENT FUNCTIONS
// ============================================================================

export function showChangePasswordModal() {
    document.getElementById('changePasswordForm').reset();
    document.getElementById('changePasswordError').style.display = 'none';
    document.getElementById('changePasswordSuccess').style.display = 'none';
    document.getElementById('changePasswordModal').style.display = 'block';
}

export function closeChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
    document.getElementById('changePasswordForm').reset();
}

export async function submitChangePassword(event) {
    event.preventDefault();

    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('changeNewPassword').value;
    const confirmPassword = document.getElementById('changeConfirmPassword').value;

    const errorDiv = document.getElementById('changePasswordError');
    const successDiv = document.getElementById('changePasswordSuccess');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'Die neuen Passwörter stimmen nicht überein.';
        errorDiv.style.display = 'block';
        return;
    }

    if (newPassword.length < 8) {
        errorDiv.textContent = 'Das neue Passwort muss mindestens 8 Zeichen lang sein.';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/change-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() || '' },
            credentials: 'include',
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword
            })
        });

        if (response.ok) {
            successDiv.textContent = 'Passwort erfolgreich geändert!';
            successDiv.style.display = 'block';
            document.getElementById('changePasswordForm').reset();
            setTimeout(() => {
                closeChangePasswordModal();
            }, 2000);
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Ändern des Passworts';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error changing password:', error);
        errorDiv.textContent = 'Fehler beim Ändern des Passworts';
        errorDiv.style.display = 'block';
    }
}

export function showForgotPasswordModal() {
    closeLoginModal();
    document.getElementById('forgotPasswordForm').reset();
    document.getElementById('forgotPasswordError').style.display = 'none';
    document.getElementById('forgotPasswordSuccess').style.display = 'none';
    document.getElementById('forgotPasswordModal').style.display = 'block';
}

export function closeForgotPasswordModal() {
    document.getElementById('forgotPasswordModal').style.display = 'none';
    document.getElementById('forgotPasswordForm').reset();
}

export async function submitForgotPassword(event) {
    event.preventDefault();

    const email = document.getElementById('forgotPasswordEmail').value;

    const errorDiv = document.getElementById('forgotPasswordError');
    const successDiv = document.getElementById('forgotPasswordSuccess');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: email })
        });

        if (response.ok) {
            const data = await response.json();
            successDiv.textContent = data.message || 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zurücksetzen des Passworts gesendet.';
            successDiv.style.display = 'block';
            document.getElementById('forgotPasswordForm').reset();
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Anfordern des Passwort-Resets';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error requesting password reset:', error);
        errorDiv.textContent = 'Fehler beim Anfordern des Passwort-Resets';
        errorDiv.style.display = 'block';
    }
}

export function checkPasswordResetToken() {
    const hash = window.location.hash;
    if (hash.startsWith('#/reset-password?token=')) {
        const token = hash.split('token=')[1];
        showResetPasswordModal(token);
    }
}

export function showResetPasswordModal(token) {
    document.getElementById('resetToken').value = token;
    document.getElementById('resetPasswordForm').reset();
    document.getElementById('resetPasswordError').style.display = 'none';
    document.getElementById('resetPasswordSuccess').style.display = 'none';
    document.getElementById('resetPasswordModal').style.display = 'block';

    validateResetToken(token);
}

export function closeResetPasswordModal() {
    document.getElementById('resetPasswordModal').style.display = 'none';
    document.getElementById('resetPasswordForm').reset();
    window.location.hash = '';
}

export async function validateResetToken(token) {
    try {
        const response = await fetch(`${API_BASE}/auth/validate-reset-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ token: token })
        });

        if (response.ok) {
            const data = await response.json();
            if (!data.valid) {
                const errorDiv = document.getElementById('resetPasswordError');
                errorDiv.textContent = 'Der Reset-Link ist ungültig oder abgelaufen.';
                errorDiv.style.display = 'block';
                document.getElementById('resetPasswordForm').querySelectorAll('input, button[type="submit"]').forEach(el => {
                    el.disabled = true;
                });
            }
        }
    } catch (error) {
        console.error('Error validating reset token:', error);
    }
}

export async function submitResetPassword(event) {
    event.preventDefault();

    const token = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    const errorDiv = document.getElementById('resetPasswordError');
    const successDiv = document.getElementById('resetPasswordSuccess');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'Die Passwörter stimmen nicht überein.';
        errorDiv.style.display = 'block';
        return;
    }

    if (newPassword.length < 8) {
        errorDiv.textContent = 'Das Passwort muss mindestens 8 Zeichen lang sein.';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                token: token,
                newPassword: newPassword
            })
        });

        if (response.ok) {
            successDiv.textContent = 'Passwort erfolgreich zurückgesetzt! Sie können sich jetzt anmelden.';
            successDiv.style.display = 'block';
            document.getElementById('resetPasswordForm').reset();
            setTimeout(() => {
                closeResetPasswordModal();
                showLoginModal();
            }, 2000);
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Zurücksetzen des Passworts';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error resetting password:', error);
        errorDiv.textContent = 'Fehler beim Zurücksetzen des Passworts';
        errorDiv.style.display = 'block';
    }
}

export function initPasswordResetCheck() {
    checkPasswordResetToken();
}
