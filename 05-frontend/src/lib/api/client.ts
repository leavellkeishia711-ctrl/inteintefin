export const fetchTransactions = async (params: Record<string, unknown>) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value.toString());
    });

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/transactions?${searchParams.toString()}`);
    if (!res.ok) {
        throw new Error('Failed to fetch transactions');
    }
    return res.json();
};

export const createTransaction = async (data: Record<string, unknown>) => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        throw new Error('Failed to create transaction');
    }
    return res.json();
};

export const uploadCsv = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/imports/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        throw new Error('Failed to upload CSV');
    }
    return res.json();
};

export const commitImport = async (batchId: string, columnMapping: Record<string, string>) => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/imports/${batchId}/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId, column_mapping: columnMapping }),
    });
    if (!res.ok) {
        throw new Error('Failed to commit import');
    }
    return res.json();
};

