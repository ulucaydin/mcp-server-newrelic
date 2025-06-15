package sampling

import (
	"context"
	"fmt"
	"math/rand"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// RandomSamplingStrategy implements random sampling
type RandomSamplingStrategy struct {
	nrdb discovery.NRDBClient
}

func (s *RandomSamplingStrategy) Sample(ctx context.Context, params discovery.SamplingParams) (*discovery.DataSample, error) {
	// Build query with random sampling
	query := fmt.Sprintf(
		"SELECT * FROM %s SINCE %d minutes ago UNTIL %d minutes ago LIMIT %d",
		params.EventType,
		int(time.Since(params.TimeRange.End).Minutes()),
		int(time.Since(params.TimeRange.Start).Minutes()),
		params.MaxSamples,
	)
	
	result, err := s.nrdb.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	
	// Get total count
	countQuery := fmt.Sprintf(
		"SELECT count(*) FROM %s SINCE %d minutes ago UNTIL %d minutes ago",
		params.EventType,
		int(time.Since(params.TimeRange.End).Minutes()),
		int(time.Since(params.TimeRange.Start).Minutes()),
	)
	
	countResult, err := s.nrdb.Query(ctx, countQuery)
	if err != nil {
		return nil, err
	}
	
	var totalCount int64
	if len(countResult.Results) > 0 {
		if count, ok := countResult.Results[0]["count"].(float64); ok {
			totalCount = int64(count)
		}
	}
	
	return &discovery.DataSample{
		EventType:    params.EventType,
		Records:      result.Results,
		SampleSize:   len(result.Results),
		TotalSize:    totalCount,
		SamplingRate: float64(len(result.Results)) / float64(totalCount),
		Strategy:     "random",
		TimeRange:    params.TimeRange,
		Metadata:     map[string]interface{}{},
	}, nil
}

func (s *RandomSamplingStrategy) EstimateSampleSize(totalRecords int64) int64 {
	// Simple heuristic: sample up to 1% or 10k records
	sampleSize := totalRecords / 100
	if sampleSize > 10000 {
		sampleSize = 10000
	}
	if sampleSize < 100 {
		sampleSize = min(totalRecords, 100)
	}
	return sampleSize
}

func (s *RandomSamplingStrategy) GetStrategyName() string {
	return "random"
}

// StratifiedSamplingStrategy implements stratified sampling
type StratifiedSamplingStrategy struct {
	nrdb discovery.NRDBClient
}

func (s *StratifiedSamplingStrategy) Sample(ctx context.Context, params discovery.SamplingParams) (*discovery.DataSample, error) {
	// For now, implement as time-based stratified sampling
	// Divide time range into strata and sample from each
	
	numStrata := 10
	strataDuration := params.TimeRange.End.Sub(params.TimeRange.Start) / time.Duration(numStrata)
	samplesPerStratum := params.MaxSamples / int64(numStrata)
	
	allRecords := make([]map[string]interface{}, 0, params.MaxSamples)
	
	for i := 0; i < numStrata; i++ {
		strataStart := params.TimeRange.Start.Add(time.Duration(i) * strataDuration)
		strataEnd := strataStart.Add(strataDuration)
		
		query := fmt.Sprintf(
			"SELECT * FROM %s SINCE %d minutes ago UNTIL %d minutes ago LIMIT %d",
			params.EventType,
			int(time.Since(strataEnd).Minutes()),
			int(time.Since(strataStart).Minutes()),
			samplesPerStratum,
		)
		
		result, err := s.nrdb.Query(ctx, query)
		if err != nil {
			return nil, err
		}
		
		allRecords = append(allRecords, result.Results...)
	}
	
	return &discovery.DataSample{
		EventType:    params.EventType,
		Records:      allRecords,
		SampleSize:   len(allRecords),
		Strategy:     "stratified",
		TimeRange:    params.TimeRange,
		Metadata: map[string]interface{}{
			"strata_count": numStrata,
		},
	}, nil
}

func (s *StratifiedSamplingStrategy) EstimateSampleSize(totalRecords int64) int64 {
	// Similar to random but ensure we get good coverage
	sampleSize := totalRecords / 50 // 2%
	if sampleSize > 20000 {
		sampleSize = 20000
	}
	if sampleSize < 500 {
		sampleSize = min(totalRecords, 500)
	}
	return sampleSize
}

func (s *StratifiedSamplingStrategy) GetStrategyName() string {
	return "stratified"
}

// AdaptiveSamplingStrategy adapts sampling based on data characteristics
type AdaptiveSamplingStrategy struct {
	nrdb discovery.NRDBClient
}

func (s *AdaptiveSamplingStrategy) Sample(ctx context.Context, params discovery.SamplingParams) (*discovery.DataSample, error) {
	// Start with a small sample to understand data characteristics
	initialQuery := fmt.Sprintf(
		"SELECT * FROM %s SINCE %d minutes ago LIMIT 100",
		params.EventType,
		int(time.Since(params.TimeRange.Start).Minutes()),
	)
	
	initialResult, err := s.nrdb.Query(ctx, initialQuery)
	if err != nil {
		return nil, err
	}
	
	// Analyze initial sample to determine best approach
	// For now, just use random sampling
	// TODO: Implement adaptive logic based on data characteristics
	
	random := &RandomSamplingStrategy{nrdb: s.nrdb}
	return random.Sample(ctx, params)
}

func (s *AdaptiveSamplingStrategy) EstimateSampleSize(totalRecords int64) int64 {
	// Adaptive sizing based on total records
	switch {
	case totalRecords < 10000:
		return totalRecords // Sample everything
	case totalRecords < 100000:
		return totalRecords / 10 // 10%
	case totalRecords < 1000000:
		return totalRecords / 100 // 1%
	default:
		return min(totalRecords/1000, 50000) // 0.1% up to 50k
	}
}

func (s *AdaptiveSamplingStrategy) GetStrategyName() string {
	return "adaptive"
}

// ReservoirSamplingStrategy implements reservoir sampling for streaming data
type ReservoirSamplingStrategy struct {
	nrdb discovery.NRDBClient
}

func (s *ReservoirSamplingStrategy) Sample(ctx context.Context, params discovery.SamplingParams) (*discovery.DataSample, error) {
	// NRDB doesn't support true streaming, so simulate with batches
	reservoirSize := int(params.MaxSamples)
	reservoir := make([]map[string]interface{}, 0, reservoirSize)
	
	// Process in time-based batches
	batchDuration := 5 * time.Minute
	currentTime := params.TimeRange.Start
	recordsSeen := 0
	
	for currentTime.Before(params.TimeRange.End) {
		batchEnd := currentTime.Add(batchDuration)
		if batchEnd.After(params.TimeRange.End) {
			batchEnd = params.TimeRange.End
		}
		
		query := fmt.Sprintf(
			"SELECT * FROM %s SINCE %d minutes ago UNTIL %d minutes ago",
			params.EventType,
			int(time.Since(batchEnd).Minutes()),
			int(time.Since(currentTime).Minutes()),
		)
		
		result, err := s.nrdb.Query(ctx, query)
		if err != nil {
			return nil, err
		}
		
		// Apply reservoir sampling algorithm
		for _, record := range result.Results {
			recordsSeen++
			if len(reservoir) < reservoirSize {
				reservoir = append(reservoir, record)
			} else {
				// Randomly replace elements with decreasing probability
				j := rand.Intn(recordsSeen)
				if j < reservoirSize {
					reservoir[j] = record
				}
			}
		}
		
		currentTime = batchEnd
	}
	
	return &discovery.DataSample{
		EventType:    params.EventType,
		Records:      reservoir,
		SampleSize:   len(reservoir),
		TotalSize:    int64(recordsSeen),
		SamplingRate: float64(len(reservoir)) / float64(recordsSeen),
		Strategy:     "reservoir",
		TimeRange:    params.TimeRange,
		Metadata: map[string]interface{}{
			"records_seen": recordsSeen,
		},
	}, nil
}

func (s *ReservoirSamplingStrategy) EstimateSampleSize(totalRecords int64) int64 {
	// Reservoir sampling is good for large datasets
	return min(10000, totalRecords)
}

func (s *ReservoirSamplingStrategy) GetStrategyName() string {
	return "reservoir"
}

// Helper function
func min(a, b int64) int64 {
	if a < b {
		return a
	}
	return b
}