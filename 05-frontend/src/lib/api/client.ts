import api from '@/lib/api';

export const fetchTransactions = async (params: Record<string, unknown>) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value.toString());
    });

    const res = await api.get(`/api/v1/transactions?${searchParams.toString()}`);
    return res.data;
};

export const createTransaction = async (data: Record<string, unknown>) => {
    const res = await api.post(`/api/v1/transactions`, data);
    return res.data;
};

export const uploadCsv = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post(`/api/v1/imports/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return res.data;
};

export const commitImport = async (batchId: string, columnMapping: Record<string, string>) => {
    const res = await api.post(`/api/v1/imports/${batchId}/commit`, {
        batch_id: batchId,
        column_mapping: columnMapping
    });
    return res.data;
};

