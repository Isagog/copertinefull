export interface User {
  id: string;
  email: string;
  is_active: boolean;
  last_login: string | null;
}

export interface AuthContextType {
  user: User | null;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  token: string | null;
  isInitialized: boolean;
}
