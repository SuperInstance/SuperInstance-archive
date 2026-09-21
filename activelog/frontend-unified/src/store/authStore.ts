import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AuthState, User, LoginCredentials, RegisterCredentials, AuthResponse } from '@/types/auth';

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  checkTokenExpiry: () => boolean;
  initializeAuth: () => Promise<void>;
}

type AuthStore = AuthState & AuthActions;

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      tokens: {
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
      },

      // Actions
      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(credentials),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Login failed');
          }

          const data: AuthResponse = await response.json();
          const expiresAt = Date.now() + data.expiresIn * 1000;

          set({
            user: data.user,
            isAuthenticated: true,
            isLoading: false,
            tokens: {
              accessToken: data.accessToken,
              refreshToken: data.refreshToken,
              expiresAt,
            },
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
          });
          throw error;
        }
      },

      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(credentials),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Registration failed');
          }

          const data: AuthResponse = await response.json();
          const expiresAt = Date.now() + data.expiresIn * 1000;

          set({
            user: data.user,
            isAuthenticated: true,
            isLoading: false,
            tokens: {
              accessToken: data.accessToken,
              refreshToken: data.refreshToken,
              expiresAt,
            },
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Registration failed',
          });
          throw error;
        }
      },

      logout: () => {
        // Clear tokens from server (fire and forget)
        const { tokens } = get();
        if (tokens.refreshToken) {
          fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${tokens.accessToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refreshToken: tokens.refreshToken }),
          }).catch(() => {
            // Ignore errors on logout
          });
        }

        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
          tokens: {
            accessToken: null,
            refreshToken: null,
            expiresAt: null,
          },
        });
      },

      refreshToken: async () => {
        const { tokens } = get();
        
        if (!tokens.refreshToken) {
          throw new Error('No refresh token available');
        }

        try {
          const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refreshToken: tokens.refreshToken }),
          });

          if (!response.ok) {
            throw new Error('Token refresh failed');
          }

          const data: AuthResponse = await response.json();
          const expiresAt = Date.now() + data.expiresIn * 1000;

          set({
            user: data.user,
            tokens: {
              accessToken: data.accessToken,
              refreshToken: data.refreshToken,
              expiresAt,
            },
          });
        } catch (error) {
          // If refresh fails, logout the user
          get().logout();
          throw error;
        }
      },

      updateUser: (userData: Partial<User>) => {
        const { user } = get();
        if (user) {
          set({
            user: { ...user, ...userData },
          });
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      checkTokenExpiry: (): boolean => {
        const { tokens } = get();
        if (!tokens.expiresAt) return false;
        
        // Check if token expires in the next 5 minutes
        return Date.now() >= tokens.expiresAt - 5 * 60 * 1000;
      },

      initializeAuth: async () => {
        const { tokens, checkTokenExpiry, refreshToken } = get();
        
        if (!tokens.accessToken) {
          return;
        }

        if (checkTokenExpiry()) {
          try {
            await refreshToken();
          } catch (error) {
            console.error('Failed to refresh token on initialization:', error);
          }
        } else {
          // Verify token is still valid
          try {
            const response = await fetch(`${API_BASE_URL}/auth/verify`, {
              headers: {
                'Authorization': `Bearer ${tokens.accessToken}`,
              },
            });

            if (!response.ok) {
              get().logout();
            }
          } catch (error) {
            console.error('Failed to verify token:', error);
            get().logout();
          }
        }
      },
    }),
    {
      name: 'activelog-auth',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        tokens: state.tokens,
      }),
    }
  )
);

// Auto-refresh token when it's about to expire
setInterval(() => {
  const { checkTokenExpiry, refreshToken, isAuthenticated } = useAuthStore.getState();
  
  if (isAuthenticated && checkTokenExpiry()) {
    refreshToken().catch(() => {
      // Error will be handled in the refreshToken method
    });
  }
}, 60000); // Check every minute