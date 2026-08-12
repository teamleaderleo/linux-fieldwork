#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()

old = r'''    /// Sets the refcount for a cluster. Returns freed cluster addresses.
    fn set_cluster_refcount(&mut self, address: u64, refcount: u64) -> io::Result<Vec<u64>> {
        let mut added_clusters = Vec::new();
        let mut unref_clusters = Vec::new();
        let mut refcount_set = false;
        let mut new_cluster = None;

        while !refcount_set {
            match self.refcounts.set_cluster_refcount(
                &mut self.raw_file,
                address,
                refcount,
                new_cluster.take(),
            ) {
                Ok(None) => {
                    refcount_set = true;
                }
                Ok(Some(freed_cluster)) => {
                    let mut freed = self.set_cluster_refcount(freed_cluster, 0)?;
                    unref_clusters.push(freed_cluster);
                    unref_clusters.append(&mut freed);
                    refcount_set = true;
                }
                Err(refcount::Error::EvictingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::InvalidIndex) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::NeedCluster(addr)) => {
                    new_cluster = Some((
                        addr,
                        VecCache::from_vec(self.raw_file.read_refcount_block(addr)?),
                    ));
                }
                Err(refcount::Error::NeedNewCluster) => {
                    let addr = self.get_new_cluster(None)?;
                    added_clusters.push(addr);
                    new_cluster = Some((
                        addr,
                        VecCache::new(self.refcounts.refcounts_per_block() as usize),
                    ));
                }
                Err(refcount::Error::ReadingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::RefcountOverflow { .. }) => {
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::RefblockUnaligned(_)) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EIO));
                }
            }
        }

        for addr in added_clusters {
            self.set_cluster_refcount(addr, 1)?;
        }
        Ok(unref_clusters)
    }
'''

new = r'''    /// Sets the refcount for a cluster. Returns freed cluster addresses.
    ///
    /// Refcount blocks use relocate-on-write. A replacement block must eventually
    /// own itself through the refcount metadata too, which can recursively need
    /// more refcount blocks. Keep a lazy snapshot from immediately before the
    /// first replacement allocation so allocator ENOSPC can roll the whole
    /// recursive metadata update back instead of leaving a published replacement
    /// refblock at refcount 0.
    fn set_cluster_refcount(&mut self, address: u64, refcount: u64) -> io::Result<Vec<u64>> {
        let mut refcounts_before_relocation = None;
        let mut allocated_refcount_clusters = Vec::new();
        let result = self.set_cluster_refcount_inner(
            address,
            refcount,
            &mut refcounts_before_relocation,
            &mut allocated_refcount_clusters,
        );

        if let Err(ref e) = result
            && e.raw_os_error() == Some(libc::ENOSPC)
            && let Some(refcounts) = refcounts_before_relocation.take()
        {
            self.refcounts = refcounts;
            // get_new_cluster() consumes avail_clusters in LIFO order. Restore
            // failed transaction allocations in reverse consumption order so
            // the pre-transaction allocator ordering is preserved.
            for addr in allocated_refcount_clusters.into_iter().rev() {
                self.avail_clusters.push(addr);
            }
        }

        result
    }

    fn set_cluster_refcount_inner(
        &mut self,
        address: u64,
        refcount: u64,
        refcounts_before_relocation: &mut Option<RefCount>,
        allocated_refcount_clusters: &mut Vec<u64>,
    ) -> io::Result<Vec<u64>> {
        let mut added_clusters = Vec::new();
        let mut unref_clusters = Vec::new();
        let mut refcount_set = false;
        let mut new_cluster = None;

        while !refcount_set {
            match self.refcounts.set_cluster_refcount(
                &mut self.raw_file,
                address,
                refcount,
                new_cluster.take(),
            ) {
                Ok(None) => {
                    refcount_set = true;
                }
                Ok(Some(freed_cluster)) => {
                    let mut freed = self.set_cluster_refcount_inner(
                        freed_cluster,
                        0,
                        refcounts_before_relocation,
                        allocated_refcount_clusters,
                    )?;
                    unref_clusters.push(freed_cluster);
                    unref_clusters.append(&mut freed);
                    refcount_set = true;
                }
                Err(refcount::Error::EvictingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::InvalidIndex) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::NeedCluster(addr)) => {
                    new_cluster = Some((
                        addr,
                        VecCache::from_vec(self.raw_file.read_refcount_block(addr)?),
                    ));
                }
                Err(refcount::Error::NeedNewCluster) => {
                    // NeedNewCluster is reported before RefCount mutates the
                    // target table entry, so this is the last safe point for a
                    // lazy transaction snapshot.
                    if refcounts_before_relocation.is_none() {
                        *refcounts_before_relocation = Some(self.refcounts.clone());
                    }
                    let addr = self.get_new_cluster(None)?;
                    allocated_refcount_clusters.push(addr);
                    added_clusters.push(addr);
                    new_cluster = Some((
                        addr,
                        VecCache::new(self.refcounts.refcounts_per_block() as usize),
                    ));
                }
                Err(refcount::Error::ReadingRefCounts(e)) => {
                    return Err(e);
                }
                Err(refcount::Error::RefcountOverflow { .. }) => {
                    return Err(io::Error::from_raw_os_error(EINVAL));
                }
                Err(refcount::Error::RefblockUnaligned(_)) => {
                    self.set_corrupt_bit_best_effort();
                    return Err(io::Error::from_raw_os_error(EIO));
                }
            }
        }

        for addr in added_clusters {
            let mut freed = self.set_cluster_refcount_inner(
                addr,
                1,
                refcounts_before_relocation,
                allocated_refcount_clusters,
            )?;
            unref_clusters.append(&mut freed);
        }
        Ok(unref_clusters)
    }
'''

if old not in text:
    raise SystemExit("set_cluster_refcount anchor missing")

path.write_text(text.replace(old, new, 1))
