export interface Document {
  document_id: string;
  authorization_id?: string;
  file_name: string;
  document_type: string;
  file_type?: string;
  file_size?: number;
  status: string;
  uploaded_at: string;
  url?: string;
}
