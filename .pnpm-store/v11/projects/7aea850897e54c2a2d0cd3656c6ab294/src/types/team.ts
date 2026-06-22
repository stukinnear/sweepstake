export interface TeamRead {
  id: number
  name: string
  iso_code: string | null
  image_url: string | null
  external_provider: string | null
  external_id: string | null
  tournament_id: number
  group_id: number | null
  group_name: string | null
}

export type Team = TeamRead

export interface TeamCreate {
  name: string
  tournament_id: number
  iso_code?: string
  image_url?: string
  external_provider?: string
  external_id?: string
  group_id?: number
}

export type TeamUpdate = Partial<Omit<TeamCreate, 'tournament_id'>>
