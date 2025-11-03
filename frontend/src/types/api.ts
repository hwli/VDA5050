export type LoginPayload = {
  username: string
  password: string
}

export type LoginResponse = {
  token: string
}

export type UserProfile = {
  username: string
}

export type LogDescriptor = {
  name: string
  size: number
  modifiedAt: string
}

export type UpgradeResponse = {
  message: string
  filename: string
}
