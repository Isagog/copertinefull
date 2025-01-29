export const PASSWORD_CONFIG = {
  MIN_LENGTH: 8,
  // Future configurations (currently disabled)
  // REQUIRE_UPPERCASE: false,
  // REQUIRE_LOWERCASE: false,
  // REQUIRE_NUMBERS: false,
  // REQUIRE_SPECIAL: false,
  // SPECIAL_CHARS: '!@#$%^&*(),.?":{}|<>'
} as const;

export const validatePassword = (password: string): string[] => {
  const errors: string[] = [];
  
  if (password.length < PASSWORD_CONFIG.MIN_LENGTH) {
    errors.push(`Password must be at least ${PASSWORD_CONFIG.MIN_LENGTH} characters long`);
  }

  // Future validations (currently disabled)
  /*
  if (PASSWORD_CONFIG.REQUIRE_UPPERCASE && !/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  if (PASSWORD_CONFIG.REQUIRE_LOWERCASE && !/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  if (PASSWORD_CONFIG.REQUIRE_NUMBERS && !/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }
  if (PASSWORD_CONFIG.REQUIRE_SPECIAL && !new RegExp(`[${PASSWORD_CONFIG.SPECIAL_CHARS}]`).test(password)) {
    errors.push('Password must contain at least one special character');
  }
  */

  return errors;
};
