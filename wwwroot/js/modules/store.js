// ============================================================================
// CENTRAL STATE STORE - Observer pattern, no external framework
// ============================================================================

class Store {
    constructor(initialState = {}) {
        this._state = { ...initialState };
        this._listeners = {};
    }

    /**
     * Update a state value and notify subscribers.
     * @param {string} key
     * @param {*} value
     */
    setState(key, value) {
        this._state[key] = value;
        if (this._listeners[key]) {
            this._listeners[key].forEach(cb => {
                try { cb(value); } catch (e) { console.error('Store subscriber error:', e); }
            });
        }
    }

    /**
     * Get the current value for a key.
     * @param {string} key
     * @returns {*}
     */
    getState(key) {
        return this._state[key];
    }

    /**
     * Subscribe to changes on a key.
     * @param {string} key
     * @param {function} callback - called with the new value when state changes
     * @returns {function} unsubscribe function
     */
    subscribe(key, callback) {
        if (!this._listeners[key]) {
            this._listeners[key] = [];
        }
        this._listeners[key].push(callback);
        return () => {
            this._listeners[key] = this._listeners[key].filter(cb => cb !== callback);
        };
    }
}

// Singleton store instance with initial state
export const store = new Store({
    cachedEmployees: [],
    cachedTeams: [],
    cachedShiftTypes: [],
    allShifts: [],
    currentView: 'schedule',
});

export default store;
